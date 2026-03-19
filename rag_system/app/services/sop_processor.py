"""
SOP Document Processor — Advanced Edition
==========================================
Specialized processor for Standard Operating Procedures, Policy Documents,
and Structured Manuals.  Chunks by procedure unit rather than character count.

Strategy
--------
1. Table-first extraction  — pdfplumber table rows → direct column mapping
   (most accurate; preserves exact cell values)
2. Text-fallback parsing   — state-machine boundary detection on raw text
   (used when no structured tables are found)
3. Common post-processing  — bleed removal, section/doc context injection,
   compliance tag detection, priority inference, parent-procedure linking
"""
import re
import uuid
import pdfplumber
from typing import List, Dict, Any, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────────────────────
#  Column-name normalisation map
#  Maps raw PDF header strings (lower-cased, whitespace-collapsed)
#  → canonical field keys used throughout this module
# ─────────────────────────────────────────────────────────────────────────────
_COL_MAP: Dict[str, str] = {
    # Step / No. column
    "no":                      "step_no",
    "no.":                     "step_no",
    "#":                       "step_no",
    "step":                    "step_no",
    "step no":                 "step_no",
    "step no.":                "step_no",
    "procedure no":            "step_no",
    "procedure no.":           "step_no",
    "step/procedure no.":      "step_no",
    "step/procedure no":       "step_no",
    # Procedure text
    "procedure":               "procedure",
    "procedures":              "procedure",
    "process":                 "procedure",
    "activity":                "procedure",
    "description":             "procedure",
    "steps":                   "procedure",
    # Control objective
    "control objective":       "control_objective",
    "control":                 "control_objective",
    "objective":               "control_objective",
    # Control owner
    "control owner":           "control_owner",
    "owner":                   "control_owner",
    "responsible":             "control_owner",
    # Performed by
    "performed by":            "performed_by",
    "performed_by":            "performed_by",
    "by":                      "performed_by",
    # Communication channel
    "communication channel":   "communication_channel",
    "channel":                 "communication_channel",
    "communication":           "communication_channel",
    # Reference document
    "reference document":      "reference_document",
    "reference":               "reference_document",
    "ref.":                    "reference_document",
    "ref":                     "reference_document",
    "document":                "reference_document",
}

# Cell values that represent "empty / not applicable"
# Only truly empty / placeholder values — NOT domain-specific column headers,
# which may be legitimate content in documents outside IT/SOP.
_NULL_VALUES: Set[str] = {
    "", "-", "--", "–", "—",
    "n/a", "na", "nil", "none", "n.a.", "not applicable",
    "tbd", "to be determined", "pending", "unknown",
}

# ─────────────────────────────────────────────────────────────────────────────
#  Compliance-framework detection
# ─────────────────────────────────────────────────────────────────────────────
_COMPLIANCE_PATTERNS: Dict[str, re.Pattern] = {
    "ISO 27001": re.compile(r"iso\s*27001|isms",                          re.IGNORECASE),
    "ISO 9001":  re.compile(r"iso\s*9001",                                re.IGNORECASE),
    "GDPR":      re.compile(r"\bgdpr\b|data\s+protection\s+regulation",   re.IGNORECASE),
    "NIST":      re.compile(r"\bnist\b",                                  re.IGNORECASE),
    "PCI-DSS":   re.compile(r"\bpci[\s\-]?dss\b|\bpci\b",                re.IGNORECASE),
    "SOC 2":     re.compile(r"\bsoc\s*2\b",                               re.IGNORECASE),
    "HIPAA":     re.compile(r"\bhipaa\b",                                 re.IGNORECASE),
}

# Priority keyword patterns
_HIGH_PRIORITY = re.compile(
    r"\b(critical|mandatory|must|shall|required|immediately|urgent|prohibited|compulsory)\b",
    re.IGNORECASE,
)
_LOW_PRIORITY = re.compile(
    r"\b(optional|recommended|should|may|where\s+applicable|where\s+possible)\b",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Category keyword map  (scored — all categories evaluated, best wins)
# ─────────────────────────────────────────────────────────────────────────────
_CATEGORIES: Dict[str, List[str]] = {
    "IT Planning & Strategy":   [
        "annual plan", "it plan", "requirement planning", "irp meeting",
        "budget", "strategy", "cto", "cio", "ciso",
    ],
    "Physical Security":        [
        "physical security", "equipment rack", "lockable rack", "cctv",
        "badge access", "restricted area", "server room",
    ],
    "Asset Management":         [
        "asset", "inventory", "procurement", "purchase", "laptop",
        "desktop", "hardware purchase", "computer system",
    ],
    "User Management":          [
        "new employee", "new hire", "onboarding", "offboarding",
        "user account", "employee laptop",
    ],
    "Network Security":         [
        "network", "firewall", "vpn", "switching", "router",
        "wifi", "connectivity", "infrastructure",
    ],
    "Access Control":           [
        "access control", "multi-factor", "mfa", "privilege",
        "authentication", "authorization", "password policy",
    ],
    "Backup & Recovery":        [
        "backup", "recovery", "restore", "disaster recovery", "rto", "rpo",
    ],
    "Change Management":        [
        "change management", "change request", "cab", "deployment",
        "release", "change advisory",
    ],
    "Incident Management":      [
        "incident", "security event", "breach", "alert", "escalation",
        "incident response",
    ],
    "Compliance & Audit":       [
        "compliance", "audit", "regulation", "iso 27001", "sox",
        "policy review",
    ],
    "Data Protection":          [
        "data protection", "privacy", "encryption", "gdpr",
        "data classification",
    ],
    "Server Management":        [
        "server", "hardware provider", "server inspection",
        "monitoring", "patch management",
    ],
    "Service Level Agreement":  [
        "sla", "service level", "uptime", "kpi", "metrics",
    ],
}

# ───────────────────────────────────────────────────────────────────
#  Composite-header collapse map
#  If a derived column key CONTAINS one of these substrings, the column is
#  remapped to the matching canonical field.  This handles multi-segment
#  headers such as “Performed By DM IT Networks” or
#  “Cryptography Policy Performed By Head Of IT Network”.
#  Checked in order — first match wins.
# ───────────────────────────────────────────────────────────────────
_HEADER_SUBSTRINGS: List[Tuple[str, str]] = [
    # Core SOP fields — substring present in derived header key → canonical name.
    # These handle composite column headers like "Performed By DM IT Networks"
    # or "Cryptography Policy Performed By Head Of IT Network".
    # Checked in order — first match wins.
    ("performed_by",           "performed_by"),
    ("control_objective",      "control_objective"),
    ("control_owner",          "control_owner"),
    ("communication_channel",  "communication_channel"),
    ("reference_document",     "reference_document"),
    ("step_no",                "step_no"),
    # "procedure" / "process" intentionally excluded:
    # these words appear naturally in data-cell text and would cause
    # content rows to be misidentified as header rows.
    #
    # All other column-header remapping is handled dynamically in
    # _detect_headers using two pattern rules:
    #   1. Role acronyms  (e.g. CISO, CTO, GM)     → control_owner
    #   2. Long verb phrases (≥ 4 words, verb-like) → control_objective
]


class SOPProcessor:
    """
    Process SOP/policy PDF documents with intelligent procedure-based chunking.

    Extraction order:
      1. pdfplumber table extraction  → direct column → field mapping
      2. Text-mode state-machine      → regex field extraction
    Both paths share a common post-processing pipeline.
    """

    def __init__(self):
        # ── Step / numbered-item boundary pattern ─────────────────────────────────────────────
        # Matches: "Step No. 6.3.1", "Task No.: 2", "Item #3", "Protocol No. 1.2.3",
        #          standalone deep section numbers like "6.3.1" on their own line, and
        #          simple leading numbers "1." / "2." / "3." used in any numbered list.
        self._step_re = re.compile(
            r"(?:"
            r"(?:Step|Procedure|Task|Item|Protocol|Activity|Action|Stage|Phase|Point)"
            r"\s+(?:No\.?|Number|#|ID)\s*[:\-]?\s*[\d\.]+"
            r"|^\s*\d+\.\d+(?:\.\d+)+\s*$"  # standalone 6.3.1 alone on a line
            r")",
            re.IGNORECASE | re.MULTILINE,
        )

        # ── Section / chapter / heading boundary pattern ────────────────────────────────────
        # Matches Section:, Chapter:, Part:, Topic:, Module:, Unit:, Phase:, Stage:
        # \b after the keyword prevents false matches on words that merely START with
        # a keyword (e.g. "particularly" starting with "Part").
        self._section_re = re.compile(
            r"^(?:Section|Chapter|Part|Topic|Module|Unit|Phase|Stage)\b\s*[:\-]?\s*"
            r"(.+?)(?:\s*\|\s*Page:\s*\d+)?$",
            re.IGNORECASE | re.MULTILINE,
        )

        # ── Document-header pattern ──────────────────────────────────────────────────────────
        self._doc_header_re = re.compile(
            r"\[Document:\s*([^\|\]]+?)(?:\s*\|\s*Version:\s*([\d\.]+))?\]",
            re.IGNORECASE,
        )

        # ── Text-mode field patterns ──────────────────────────────────────────────────────────
        # Lookahead "_STOP" terminates multi-line captures at the next field label
        _STOP = (
            r"(?=\n\s*(?:"
            r"Control\s+O(?:bjective|wner)"
            r"|Performed\s+By"
            r"|Communication\s+Channel"
            r"|Reference\s+Document"
            r"|Step\s+(?:No|Number)"
            r"|Procedure\s+No"
            r"|\[Document"
            r"|\Z))"
        )
        self._field_re: Dict[str, re.Pattern] = {
            "step_no":               re.compile(
                r"(?:Step|Procedure)\s+(?:No\.?|Number)\s*[:\-]?\s*([\d\.]+)",
                re.IGNORECASE,
            ),
            "performed_by":          re.compile(
                r"Performed\s+By\s*:\s*([^\n]+)", re.IGNORECASE
            ),
            "procedure":             re.compile(
                r"Procedure\s*:\s*([\s\S]+?)" + _STOP, re.IGNORECASE
            ),
            "control_objective":     re.compile(
                r"Control\s+Objective\s*:\s*([\s\S]+?)" + _STOP, re.IGNORECASE
            ),
            "control_owner":         re.compile(
                r"Control\s+Owner\s*:\s*([^\n]+)", re.IGNORECASE
            ),
            "communication_channel": re.compile(
                r"Communication\s+Channel\s*:\s*([^\n]+)", re.IGNORECASE
            ),
            "reference_document":    re.compile(
                r"Reference\s+Document\s*:\s*([^\n]+)", re.IGNORECASE
            ),
            "page":                  re.compile(r"\bPage\s*:\s*(\d+)", re.IGNORECASE),
            "section":               re.compile(r"\bSection\s*:\s*([^\|\n]+)", re.IGNORECASE),
            "document":              re.compile(r"\[Document\s*:\s*([^\|\]]+)", re.IGNORECASE),
            "version":               re.compile(r"\bVersion\s*:\s*([\d\.]+)", re.IGNORECASE),
        }

        # ── Bleed-artefact patterns ───────────────────────────────────────────────────────────
        # Generic patterns only — no literal document-specific phrases
        self._bleed_res: List[re.Pattern] = [
            # "Something is approved/submitted/obtained/prepared." at end of value
            re.compile(r"\.?\s*[A-Z][^.]{3,80}\s+is\s+(?:approved|submitted|obtained|prepared|completed|reviewed)\.?$",
                       re.IGNORECASE),
            # "<Noun> is <word>." patterns
            re.compile(r"\.?\s*\w[\w\s]{3,40}\s+is\s+\w+\.?$",
                       re.IGNORECASE),
            # Dangling sentence after a period that doesn't belong to current field
            re.compile(r"(?<=\.)\s+[A-Z][^.]{10,120}(?<!\.)$"),
        ]

        # ── Persistent state across pages ───────────────────────────────────────────────────
        self._current_section: Optional[str] = None
        self._current_doc:     Optional[str] = None
        self._current_version: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════════════
    #  Public API
    # ═══════════════════════════════════════════════════════════════════

    def detect_is_sop_document(self, text: str) -> bool:
        """
        Return True if the document appears to be structured/procedural.
        Works with any domain: IT, HR, medical, compliance, etc.
        """
        indicators = [
            # IT/SOP specific
            r"(?:Step|Procedure)\s+(?:No\.?|Number)",
            r"Control\s+Objective",
            r"Control\s+Owner",
            r"Reference\s+Document",
            r"Communication\s+Channel",
            r"SOP|Standard\s+Operating\s+Procedure",
            r"Policy\s+Manual",
            r"IT\s+Department\s+Manual",
            r"Performed\s+By",
            # Generic structured-document indicators
            r"\d+\.\d+\.\d+",                  # numbered sections 3.2.1
            r"^\s*\d+[\.)\-]\s+\w",            # numbered list items
            r"Responsible\s+(?:Party|Person|Owner)",
            r"Action\s+Item",
            r"Work\s+Instruction",
            r"Process\s+Owner",
            r"Approval\s+(?:Required|Status)",
            r"Frequency|Periodicity",
        ]
        count = sum(
            1 for p in indicators
            if re.search(p, text, re.IGNORECASE | re.MULTILINE)
        )
        return count >= 2  # Low threshold — any structured doc qualifies

    def process_pdf(
        self,
        pdf_path: str,
        filename: str,
        document_id: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """
        Process SOP PDF → list of procedure-based chunks.
        Returns: (chunks, document_id, num_pages)
        """
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        self._reset_state()

        num_pages = 0
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            sample = "".join(
                (p.extract_text() or "") for p in pdf.pages[: min(5, num_pages)]
            )

        if not self.detect_is_sop_document(sample):
            print(f"  Warning: {filename} may not be an SOP document — proceeding anyway.")

        # ── 1. Try table-first extraction ─────────────────────────────────────────────
        raw_items = self._extract_via_tables(pdf_path)
        if raw_items:
            print(f"  Table extraction: {len(raw_items)} procedure rows found")
        else:
            # ── 2. Fall back to text-mode parsing ─────────────────────────────────────
            print(f"  No structured tables found — using text parsing")
            raw_items = self._extract_via_text(pdf_path)

        # ── 3. Post-process & build final chunks ──────────────────────────────────────────
        chunks: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_items):
            item = self._clean_item(item)
            if not self._is_substantive(item):
                continue
            structured_text = self._build_text(item)
            metadata        = self._build_metadata(item, doc_id, filename, idx)
            chunks.append({"text": structured_text, "metadata": metadata})

        # Patch total_chunks now the final count is known
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk["metadata"]["chunk"]        = i
            chunk["metadata"]["total_chunks"] = total

        print(f"✓ SOP Processing: {total} procedure chunks from {num_pages} pages ({filename})")
        return chunks, doc_id, num_pages
    
    # ═══════════════════════════════════════════════════════════════════
    #  Path 1 — Table-first extraction
    # ═══════════════════════════════════════════════════════════════════

    def _extract_via_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract rows from PDF tables (regular, matrices) and image references.
        Tries three table strategies in descending strictness:
          1. lines       — bordered tables with visible grid lines
          2. text        — borderless / whitespace-aligned tables
          3. lenient     — pdfplumber default (catch-all)
        """
        all_items: List[Dict[str, Any]] = []
        last_headers: Optional[Dict[int, str]] = None

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                self._update_context(page_text, page_num)

                # ── Image references on this page ─────────────────────────
                all_items.extend(self._extract_image_refs(page, page_num))

                # ── Tables: try 3 strategies ──────────────────────────────
                tables = (
                    page.extract_tables({
                        "vertical_strategy":    "lines",
                        "horizontal_strategy":  "lines",
                        "snap_tolerance":       4,
                        "join_tolerance":       4,
                        "edge_min_length":      3,
                        "min_words_vertical":   1,
                        "min_words_horizontal": 1,
                    })
                    or page.extract_tables({
                        "vertical_strategy":   "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance":      3,
                        "join_tolerance":      3,
                    })
                    or page.extract_tables()
                    or []
                )

                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers, hdr_row = self._detect_headers(table, last_headers)
                    if not headers:
                        continue

                    # Reject tables that are really flowing prose in a multi-column
                    # page layout which the text strategy mistakes for a grid table.
                    # Skip this check when hdr_row < 0 (fallback headers — continuation table).
                    if hdr_row >= 0 and self._is_word_wrap_table(table, headers, hdr_row):
                        continue

                    last_headers = headers

                    # Matrix (has row-header labels) vs flat table
                    if self._is_matrix(table, headers, hdr_row):
                        rows = self._matrix_to_items(table, headers, hdr_row)
                    else:
                        rows = []
                        for row in table[hdr_row + 1:]:
                            if not row or not any(c and str(c).strip() for c in row):
                                continue
                            it = self._row_to_item(row, headers)
                            if it:
                                rows.append(it)

                    for it in rows:
                        self._inject_context(it, page_num)
                        # Merge continuation rows (no step_no) into the previous item.
                        # This handles table rows that were split at a page boundary.
                        _MERGE_SKIP = {'page', 'section', 'document', 'version',
                                       'chunk', 'total_chunks', '_chunk_type'}
                        if not it.get('step_no') and all_items:
                            prev = all_items[-1]
                            for field, val in it.items():
                                if field in _MERGE_SKIP:
                                    continue
                                prev_val = str(prev.get(field, ''))
                                prev[field] = (prev_val + ' ' + val).strip() if prev_val else val
                        else:
                            all_items.append(it)

        return all_items

    def _detect_headers(
        self,
        table: List[List],
        fallback: Optional[Dict[int, str]],
    ) -> Tuple[Optional[Dict[int, str]], int]:
        """
        Find the header row among the first three rows.

        Rules applied in order:
        1. Skip cells that are empty, too-long (>80 chars), or purely
           numeric/dotted-numeric (e.g., \"7.1.4\", \"42\") — these are data
           values, never column labels.
        2. COL_MAP exact match for known canonical field names.
        3. Substring match via _HEADER_SUBSTRINGS to collapse composite
           headers like \"Performed By DM IT Networks\" → \"performed_by\".
        4. Fall back to derived snake_case key for any other header text.
        5. Use last_headers as fallback ONLY when the table has the same
           column count — prevents stale headers from bleeding into
           structurally different tables on later pages.
        """
        for row_idx, row in enumerate(table[:3]):
            # Skip rows that contain step-number-formatted cells (e.g. "7.2.11").
            # Such rows are procedure data rows, not column header rows.
            if any(
                cell and re.match(r'^\d+\.\d+(?:\.\d+)*\s*$', str(cell).strip())
                for cell in (row or [])
            ):
                continue
            mapping:     Dict[int, str] = {}
            known_count: int            = 0  # cells that map to a recognised field
            for col_idx, cell in enumerate(row):
                if not cell:
                    continue
                raw = str(cell).strip()
                if not raw or len(raw) > 80:
                    continue
                # Reject pure numeric / dotted-numeric cells as header keys
                # e.g., "7.1.4", "7.2.20", "42" are step-number data, not labels
                if re.match(r'^[\d.\s]+$', raw):
                    continue
                # Reject cells that look like "Label: value" data entries
                # (e.g. "Performed by: DM IT Networks", "Reference: ITD-F1").
                # Real column headers are short labels and never contain a colon
                # followed by content.
                if re.search(r'^[\w][\w\s]{2,30}:\s+\S', raw):
                    continue
                norm = " ".join(raw.lower().split())
                # Skip header cells whose normalized no-punctuation form is a
                # null/N-A token (e.g. "N/A", "N A", "N.A.", "None", "TBD").
                # This prevents null-placeholder column headers from polluting
                # the field mapping.
                _norm_nopunct = re.sub(r'[^a-z0-9]', '', norm)
                if _norm_nopunct in {re.sub(r'[^a-z0-9]', '', nv) for nv in _NULL_VALUES}:
                    continue
                # 1. COL_MAP exact match (highest confidence)
                canonical = _COL_MAP.get(norm)
                if canonical:
                    known_count += 1
                else:
                    # 2. Derive snake_case key
                    derived = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
                    # 3. Collapse composite headers via substring matching
                    canonical = derived
                    for substr, field in _HEADER_SUBSTRINGS:
                        if substr in derived:
                            canonical = field
                            known_count += 1
                            break

                    if canonical == derived:   # no substring match — try dynamic rules

                        raw_words  = raw.split()
                        first_raw  = raw_words[0] if raw_words else ""
                        first_word = derived.split("_")[0]

                        # Rule A: single role-acronym token (CISO, CTO, GM, CSO …)
                        # Raw cell is 2–5 all-uppercase letters, no spaces.
                        if re.match(r'^[A-Z]{2,5}$', raw):
                            canonical = "control_owner"
                            known_count += 1

                        # Rule A2: multi-word header whose FIRST word is a
                        # 2–5-char all-uppercase abbreviation (department / role).
                        # Examples: "DM IT Networks", "IS Officer", "HR Department"
                        # These are responsible-party columns → performed_by.
                        elif (len(raw_words) >= 2
                              and re.match(r'^[A-Z]{2,5}$', first_raw)
                              and len(raw) <= 40):
                            canonical = "performed_by"
                            known_count += 1

                        # Rule B: long phrase column (≥ 4 word tokens).
                        # Split by intent of the first word:
                        #   B1 — "To [verb] …"  (infinitive purpose clause)
                        #          → control_objective
                        #   B2 — purpose verb  (ensure, protect, maintain …)
                        #          → control_objective
                        #   B3 — anything else with ≥ 4 words
                        #          → procedure  (action/task column title)
                        elif derived.count("_") >= 3:
                            _PURPOSE = {
                                "ensure", "protect", "maintain", "provide",
                                "support", "promote", "foster", "evaluate",
                                "establish", "prevent", "monitor", "manage",
                                "enable", "achieve", "define", "enhance",
                                "reduce", "address", "implement", "detect",
                            }
                            if first_word == "to" or first_word in _PURPOSE:
                                canonical = "control_objective"
                            else:
                                canonical = "procedure"
                            known_count += 1

                if canonical:
                    mapping[col_idx] = canonical
            # Accept as a header row ONLY when:
            #   • >= 2 columns were mapped, AND
            #   • >= 1 column maps to a recognised canonical field
            # This prevents data rows (e.g. "DM IT Networks / | CTO | ITD-P1-F8")
            # from being mistaken for header rows.
            if len(mapping) >= 2 and known_count >= 1:
                return mapping, row_idx

        # Use fallback when column count matches or the table fits within fallback width.
        # This handles page-boundary transitions where the header-row page used merged
        # cells (making a wider column count) but subsequent pages have plain data rows
        # with fewer columns — both are part of the same logical table.
        if fallback is not None:
            table_width    = max((len(row) for row in table if row), default=0)
            fallback_width = (max(fallback.keys()) + 1) if fallback else 0
            if 0 < table_width <= fallback_width:
                # hdr_row=-1 means no header row detected on this page;
                # treat ALL rows as data (handles cross-page table continuations).
                return fallback, -1

        return None, 0

    def _row_to_item(
        self,
        row: List,
        headers: Dict[int, str],
    ) -> Optional[Dict[str, Any]]:
        """Map a table row to a field dict via the column→name mapping."""
        item: Dict[str, Any] = {}
        for col_idx, field_name in headers.items():
            if col_idx >= len(row):
                continue
            cell = row[col_idx]
            val  = " ".join(str(cell).strip().split()) if cell else ""
            if val and val.lower() not in _NULL_VALUES:
                item[field_name] = val
        return item if len(item) >= 2 else None

    def _is_matrix(
        self,
        table: List[List],
        headers: Dict[int, str],
        hdr_row: int,
    ) -> bool:
        """
        Return True if the table is a matrix — i.e., column 0 contains
        meaningful text row-labels across most data rows.
        Examples: RACI matrix, risk matrix, competency matrix.

        NOT a matrix when:
        - col-0 is the step/procedure number column  (step_no / no)
        - col-0 values are dotted numeric IDs like 7.1.2, 8.3.2
        """
        if 0 not in headers:
            return False
        # A known step/ID column in col-0 always means a flat procedure table
        if headers.get(0) in ("step_no", "no"):
            return False
        data_rows = table[hdr_row + 1:]
        if len(data_rows) < 2:
            return False
        label_count = 0
        for row in data_rows:
            if not row:
                continue
            cell = str(row[0]).strip() if row[0] else ""
            # A valid row-label: non-empty, not a null value,
            # not a pure numeric/dotted ID (e.g. 7, 7.1, 7.1.2)
            if cell and cell.lower() not in _NULL_VALUES and not re.match(r"^[\d.]+$", cell):
                label_count += 1
        return label_count >= max(2, len(data_rows) // 2)

    def _matrix_to_items(
        self,
        table: List[List],
        headers: Dict[int, str],
        hdr_row: int,
    ) -> List[Dict[str, Any]]:
        """
        Flatten a matrix into one item per row.
        Each item carries the row-label plus every column value,
        preserving the full row × column relationship.
        """
        items: List[Dict[str, Any]] = []
        for row in table[hdr_row + 1:]:
            if not row or not any(c and str(c).strip() for c in row):
                continue
            item: Dict[str, Any] = {}
            for col_idx, field_name in headers.items():
                if col_idx >= len(row):
                    continue
                cell = row[col_idx]
                val  = " ".join(str(cell).strip().split()) if cell else ""
                if val and val.lower() not in _NULL_VALUES:
                    item[field_name] = val
            if len(item) >= 2:
                item["_chunk_type"] = "matrix_row"
                items.append(item)
        return items

    def _is_word_wrap_table(
        self,
        table: List[List],
        headers: Dict[int, str],
        hdr_row: int,
    ) -> bool:
        """
        Return True when the table was almost certainly produced by the text
        strategy treating a multi-column *flowing-prose* page layout as a grid
        table.  The telltale sign is word-wrap artefacts: adjacent cells contain
        the two halves of a single word split at the column boundary.

        Detection: cell[i] ends with a letter AND cell[i+1] starts with a
        lowercase letter across ≥ 25 % of all adjacent non-empty cell pairs
        (checked in all rows, including the header row).

        Examples that should be rejected:
          "It Outlines The Stan" | "dardized"   (Stan + dardized = Standardized)
          "defining the hier"    | "archy, repo" (hier + archy = hierarchy)
          "services w"           | "hile ensuring compli" (w + hile = while)
        """
        col_indices = sorted(headers.keys())
        if len(col_indices) < 2:
            return False

        pairs_total  = 0
        pairs_broken = 0

        # Sample all rows (header + data rows)
        for row in table[hdr_row:]:
            if not row:
                continue
            cells = [
                str(row[ci]).strip() if ci < len(row) and row[ci] else ""
                for ci in col_indices
            ]
            for i in range(len(cells) - 1):
                a, b = cells[i], cells[i + 1]
                if a and b:
                    pairs_total += 1
                    # Word was split: left half ends with a letter, right half
                    # starts with a lowercase letter (continuation of the word).
                    if a[-1].isalpha() and b[0].islower():
                        pairs_broken += 1

        if pairs_total == 0:
            return False
        return (pairs_broken / pairs_total) >= 0.25

    def _extract_image_refs(
        self,
        page: Any,
        page_num: int,
    ) -> List[Dict[str, Any]]:
        """
        Detect embedded images on a page and capture surrounding text
        (figure title above, caption below) as context.
        Returns one item per image that has associated text context.
        """
        items: List[Dict[str, Any]] = []
        try:
            images = page.images
        except Exception:
            return items

        page_w = float(page.width)
        page_h = float(page.height)

        for seq, img in enumerate(images, 1):
            try:
                # pdfplumber uses 'top'/'bottom' in page coordinate space
                x0 = float(img.get("x0", 0))
                y0 = float(img.get("top",  img.get("y0", 0)))
                x1 = float(img.get("x1", 0))
                y1 = float(img.get("bottom", img.get("y1", 0)))
            except (TypeError, ValueError):
                continue

            if x0 >= x1 or y0 >= y1:
                continue

            bx0 = max(0.0, x0 - 10)
            bx1 = min(page_w, x1 + 10)
            title = caption = ""

            # Text immediately above the image (label / figure number)
            try:
                pad  = min(60.0, y0)
                crop = page.within_bbox((bx0, max(0.0, y0 - pad), bx1, y0))
                txt  = (crop.extract_text() or "").strip()
                if txt:
                    title = " ".join(txt.split())
            except Exception:
                pass

            # Text immediately below the image (caption)
            try:
                pad  = min(70.0, page_h - y1)
                crop = page.within_bbox((bx0, y1, bx1, min(page_h, y1 + pad)))
                txt  = (crop.extract_text() or "").strip()
                if txt:
                    caption = " ".join(txt.split())
            except Exception:
                pass

            # Strip any leading section-number prefix such as "6.3 " or "12.1.2 "
            # or "6.3. " (with trailing period, common in formal document headings)
            # that pdfplumber may pick up from the area around the image.
            # "6.3. Planning Procedures"  → "Planning Procedures"
            # "6.3 Annual IT Security Plan" → "Annual IT Security Plan"
            # "6.3"                         → "6.3"  (no trailing text, unchanged)
            _sec_prefix = re.compile(r'^\d+(?:\.\d+)*\.?\s+')
            title   = _sec_prefix.sub('', title).strip()
            caption = _sec_prefix.sub('', caption).strip()

            # Real figure text must be substantive (>= 15 chars, not purely numeric)
            def _is_real_text(t: str) -> bool:
                return bool(t) and len(t) >= 15 and not re.match(r'^[\d.\s]+$', t)

            title_ok   = _is_real_text(title)
            caption_ok = _is_real_text(caption)

            # If the title looks like a real caption and caption looks like a
            # section reference, swap them so the context makes more sense.
            if not title_ok and caption_ok:
                title, caption = caption, ""
                title_ok, caption_ok = True, False

            if not title_ok and not caption_ok:
                continue

            item: Dict[str, Any] = {
                "image_ref":   f"Figure {page_num}-{seq}",
                "page":        str(page_num),
                "_chunk_type": "image_reference",
            }
            if title_ok:
                item["figure_title"] = title
            if caption_ok:
                item["caption"] = caption
            self._inject_context(item, page_num)
            items.append(item)

        return items

    # ═══════════════════════════════════════════════════════════════════
    #  Path 2 — Text-fallback extraction
    # ═══════════════════════════════════════════════════════════════════

    def _extract_via_text(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Parse raw PDF text using a state-machine to find procedure blocks."""
        full_text, _ = self._extract_full_text(pdf_path)
        blocks = self._split_blocks(full_text)
        blocks = self._merge_orphans(blocks)
        return [item for item in (self._parse_block(b) for b in blocks) if item]

    def _extract_full_text(self, pdf_path: str) -> Tuple[str, int]:
        """Extract full text with PAGE markers."""
        parts: List[str] = []
        num_pages = 0
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                if text.strip():
                    parts.append(f"\n\n--- PAGE {page_num} ---\n{text}")
        return "".join(parts), num_pages

    def _split_blocks(self, text: str) -> List[str]:
        """State-machine: split text into one block per procedure."""
        blocks:  List[str] = []
        current: List[str] = []
        in_block            = False

        for line in text.split("\n"):
            stripped = line.strip()

            if re.match(r"^\[Document:", stripped, re.IGNORECASE):
                if current and in_block:
                    blocks.append("\n".join(current))
                current  = [line]
                in_block = False
                continue

            sec_m = self._section_re.search(stripped)
            if sec_m and not in_block:
                candidate = sec_m.group(1).strip().rstrip("|").strip()
                # Accept only plausible-length headings; reject prose sentences
                if 5 < len(candidate) < 100 and not re.match(
                    r"^(?:page|no|step)", candidate, re.IGNORECASE
                ):
                    self._current_section = candidate
                current.append(line)
                continue

            if self._step_re.search(stripped):
                if current and in_block:
                    blocks.append("\n".join(current))
                current  = [line]
                in_block = True
                continue

            if stripped or current:
                current.append(line)
                # Trigger block start on any 'Label: value' line — not just IT-specific ones
                if not in_block and re.search(
                    r"^[A-Z][A-Za-z0-9 /\-]{2,40}?:\s*\S", stripped
                ):
                    in_block = True

        if current and in_block:
            blocks.append("\n".join(current))

        if not blocks:
            blocks = [p.strip() for p in re.split(r"--- PAGE \d+ ---", text) if p.strip()]

        return blocks

    def _merge_orphans(self, blocks: List[str]) -> List[str]:
        """Append short no-step fragments to the previous block."""
        if not blocks:
            return blocks
        merged = [blocks[0]]
        for block in blocks[1:]:
            has_step = bool(self._step_re.search(block))
            is_short = len(block.strip()) < 300
            if not has_step and is_short:
                merged[-1] = merged[-1].rstrip() + "\n" + block.strip()
            else:
                merged.append(block)
        return merged

    def _parse_block(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract all structured fields from a text block.
        First applies known field patterns, then falls back to a generic
        'Label: Value' scanner so unknown document types are captured too.
        """
        item: Dict[str, Any] = {}

        # Pass 1 — known field patterns (precise, with stop-lookaheads)
        for field_name, pattern in self._field_re.items():
            m = pattern.search(text)
            if m:
                val = " ".join(m.group(1).strip().split())
                if val and val.lower() not in _NULL_VALUES:
                    item[field_name] = val

        # Pass 2 — generic 'Label: value' scan for any unlabelled document type
        generic_re = re.compile(
            r"^([A-Z][A-Za-z0-9 /\-]{2,40}?)\s*:\s*(.{5,})", re.MULTILINE
        )
        for m in generic_re.finditer(text):
            key = re.sub(r"[^a-z0-9]+", "_", m.group(1).strip().lower()).strip("_")
            val = " ".join(m.group(2).strip().split())
            if key and key not in item and val and val.lower() not in _NULL_VALUES:
                item[key] = val

        item.setdefault("section",  self._current_section or "")
        item.setdefault("document", self._current_doc     or "")
        item.setdefault("version",  self._current_version or "")
        return {k: v for k, v in item.items() if v} or None

    # ═══════════════════════════════════════════════════════════════════
    #  Context tracking across pages
    # ═══════════════════════════════════════════════════════════════════

    def _reset_state(self):
        self._current_section = None
        self._current_doc     = None
        self._current_version = None

    def _update_context(self, page_text: str, page_num: int):
        doc_m = self._doc_header_re.search(page_text)
        if doc_m:
            self._current_doc = doc_m.group(1).strip()
            if doc_m.group(2):
                self._current_version = doc_m.group(2).strip()

        for line in page_text.split("\n"):
            sec_m = self._section_re.search(line.strip())
            if sec_m:
                candidate = sec_m.group(1).strip().rstrip("|").strip()
                # Accept only plausible-length headings; reject prose sentences
                if 5 < len(candidate) < 100 and not re.match(
                    r"^(?:page|no|step)", candidate, re.IGNORECASE
                ):
                    self._current_section = candidate
                break

    def _inject_context(self, item: Dict[str, Any], page_num: int):
        item.setdefault("page", str(page_num))
        if self._current_section and "section" not in item:
            item["section"] = self._current_section
        if self._current_doc and "document" not in item:
            item["document"] = self._current_doc
        if self._current_version and "version" not in item:
            item["version"] = self._current_version

    # ═══════════════════════════════════════════════════════════════════
    #  Field cleaning
    # ═══════════════════════════════════════════════════════════════════

    def _clean_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Clean every string value, drop null/empty entries."""
        # These fields carry structured text that must NOT be run through
        # the bleed / orphan-label cleaners (they would strip meaningful content)
        _NO_CLEAN = {"figure_title", "caption"}
        result: Dict[str, Any] = {}
        for k, v in item.items():
            if not isinstance(v, str):
                result[k] = v
                continue
            if k in _NO_CLEAN:
                cleaned = " ".join(v.split()).strip(",;: \t")
            else:
                cleaned = self._clean_val(v)
            if cleaned and cleaned.lower() not in _NULL_VALUES:
                result[k] = cleaned
        return result

    def _clean_val(self, value: str) -> str:
        value = " ".join(value.split())
        for bleed_re in self._bleed_res:
            value = bleed_re.sub("", value).strip()
        # Strip trailing orphaned field-label fragments (any "Word Word:" pattern at end)
        value = re.sub(
            r"\s+[A-Z][A-Za-z0-9 /\-]{2,40}\s*:?\s*$",
            "", value,
        ).strip()
        return value.strip(".,;: \t")

    def _is_substantive(self, item: Dict[str, Any]) -> bool:
        """
        Return True if the item carries meaningful content.
        Document-agnostic: does not require any specific field name.
        """
        _SKIP = {
            "page", "document", "version", "chunk", "total_chunks",
            "section", "_chunk_type",
        }
        # Image references are always substantive if they survived _extract_image_refs
        if item.get("_chunk_type") == "image_reference":
            return True
        content = {
            k: v for k, v in item.items()
            if k not in _SKIP and isinstance(v, str) and len(v.strip()) > 5
        }
        all_text = " ".join(content.values())
        return len(content) >= 1 and len(all_text) > 30

    # ═══════════════════════════════════════════════════════════════════
    #  Chunk building
    # ═══════════════════════════════════════════════════════════════════

    def _build_image_text(self, item: Dict[str, Any]) -> str:
        """Render an image-reference item into readable text."""
        parts = [f"[Image: {item.get('image_ref', 'Figure')}]"]
        loc = []
        if item.get("page"):    loc.append(f"Page: {item['page']}")
        if item.get("section"): loc.append(f"Section: {item['section']}")
        if loc:
            parts.append(" | ".join(loc))
        if item.get("figure_title"):
            parts.append(f"\nFigure Title: {item['figure_title']}")
        if item.get("caption"):
            parts.append(f"Caption: {item['caption']}")
        return "\n".join(parts)

    def _build_text(self, item: Dict[str, Any]) -> str:
        """
        Render item fields into human-readable structured text.
        Known fields are rendered in a preferred order; any additional fields
        from other document types are appended automatically.
        """
        # Internal flags — never rendered
        _INTERNAL = {"_chunk_type"}

        if item.get("_chunk_type") == "image_reference":
            return self._build_image_text(item)

        parts: List[str] = []
        rendered: set = _INTERNAL.copy()  # pre-exclude internal keys

        # ── Header ──────────────────────────────────────────────────────
        hdr = []
        if item.get("document"):
            hdr.append(f"Document: {item['document']}")
        if item.get("version"):
            hdr.append(f"Version: {item['version']}")
        if hdr:
            parts.append(f"[{' | '.join(hdr)}]")
        rendered.update({"document", "version"})

        # ── Location ──────────────────────────────────────────────────────
        loc = []
        if item.get("page"):
            loc.append(f"Page: {item['page']}")
        if item.get("section"):
            loc.append(f"Section: {item['section']}")
        if loc:
            parts.append(" | ".join(loc))
        rendered.update({"page", "section"})

        # ── Known fields in preferred order ──────────────────────────────
        _MULTILINE = {"procedure", "control_objective"}
        _KNOWN_ORDER = [
            "step_no", "performed_by", "procedure", "control_objective",
            "control_owner", "communication_channel", "reference_document",
        ]
        for field in _KNOWN_ORDER:
            if item.get(field):
                if field == "step_no":
                    parts.append(f"\nStep/Procedure No.: {item['step_no']}")
                elif field in _MULTILINE:
                    label = field.replace("_", " ").title()
                    parts.append(f"\n{label}:\n{item[field]}")
                else:
                    label = field.replace("_", " ").title()
                    parts.append(f"{label}: {item[field]}")
                rendered.add(field)

        # ── Any extra fields specific to this document type ──────────────
        for k, v in item.items():
            if k not in rendered and isinstance(v, str) and v.strip():
                label = k.replace("_", " ").title()
                parts.append(f"{label}: {v}")
            rendered.add(k)  # prevent duplicates from the generic loop

        return "\n".join(parts) if parts else " ".join(str(v) for v in item.values())

    def _build_metadata(
        self,
        item: Dict[str, Any],
        doc_id: str,
        filename: str,
        idx: int,
    ) -> Dict[str, Any]:
        """
        Build the full metadata dict for a chunk.
        All item fields are copied — no field is ever silently dropped,
        so any document type's columns appear in the metadata automatically.
        """
        # Reserved keys managed by this method — not overwritten by item fields
        _RESERVED = {
            "document_id", "filename", "chunk", "total_chunks", "chunk_type",
            "group", "priority", "chunk_length", "compliance_tags",
            "section_id", "procedure_no", "parent_procedure",
        }
        # Determine chunk type: internal hint wins, then field-based inference
        _hint = item.get("_chunk_type", "")
        if _hint:
            _ctype = _hint
        elif any(item.get(f) for f in ("step_no", "procedure", "control_objective", "performed_by")):
            _ctype = "sop_procedure"
        else:
            _ctype = "structured_chunk"

        meta: Dict[str, Any] = {
            "document_id":  doc_id,
            "filename":     filename,
            "chunk":        idx,
            "total_chunks": 0,
            "chunk_type":   _ctype,
        }

        # Copy every item field into metadata, skipping internal-only keys
        _INTERNAL = {"_chunk_type"}
        for k, v in item.items():
            if k not in _RESERVED and k not in _INTERNAL:
                meta[k] = v

        # Convenience aliases for common filtering operations
        if item.get("section"):
            meta["section_id"] = item["section"]
        if item.get("step_no"):
            meta["procedure_no"] = item["step_no"]
            step_parts = item["step_no"].split(".")
            if len(step_parts) >= 3:
                meta["parent_procedure"] = ".".join(step_parts[:2])
            elif len(step_parts) == 2:
                meta["parent_procedure"] = step_parts[0]

        # Enrichments derived from all content
        combined = " ".join(str(v) for v in item.values() if isinstance(v, str))
        meta["group"]        = self._best_category(combined)
        meta["priority"]     = self._infer_priority(combined)
        meta["chunk_length"] = len(combined)

        tags = self._detect_compliance(combined)
        if tags:
            meta["compliance_tags"] = tags

        return meta

    # ═══════════════════════════════════════════════════════════════════
    #  Enrichment helpers
    # ═══════════════════════════════════════════════════════════════════

    def _best_category(self, text: str) -> str:
        """Score all categories and return the best-matching one."""
        t = text.lower()
        scored = {cat: sum(1 for kw in kws if kw in t) for cat, kws in _CATEGORIES.items()}
        best = max(scored, key=lambda c: scored[c])
        return best if scored[best] > 0 else "General"

    def _detect_compliance(self, text: str) -> List[str]:
        return [name for name, pat in _COMPLIANCE_PATTERNS.items() if pat.search(text)]

    def _infer_priority(self, text: str) -> str:
        if _HIGH_PRIORITY.search(text):
            return "High"
        if _LOW_PRIORITY.search(text):
            return "Medium"
        return "Normal"


# Global instance
sop_processor = SOPProcessor()
