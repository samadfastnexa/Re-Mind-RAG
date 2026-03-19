"""
Structured Document Processor — Advanced Edition
=================================================
Handles JSON, CSV, and PDF documents with structured/tabular data.

Advanced features:
- Proper logging via Python logging module
- Configurable thresholds via ProcessorConfig dataclass
- Cross-page table continuity (merges tables split across page breaks)
- Statistical column typing with confidence scores
- Chunk quality scoring (0.0–1.0 per chunk)
- Hierarchical procedure grouping (parent/child linking)
- Near-duplicate chunk detection + dedup
- Error-resilient PDF extraction with per-page fallback
- Extracted text normalization pipeline
- Performance-optimised merge-pair lookups
"""
import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

import pdfplumber
import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ProcessorConfig:
    """Tunable knobs for the Structured Processor."""

    # ── Chunk sizing ──────────────────────────────────────────────────
    min_chunk_length: int = 80        # Chunks shorter than this are merged
    max_chunk_length: int = 2000      # Warn if chunk exceeds this

    # ── Column merge ──────────────────────────────────────────────────
    merge_column_threshold: int = 8   # Only try misaligned merge above N cols
    merge_overlap_ratio: float = 0.2  # Max simultaneous-content ratio for complementary

    # ── Header detection ──────────────────────────────────────────────
    header_max_avg_len: int = 50      # Avg cell length above which row is NOT a header
    header_min_keyword_hits: int = 2  # Min SOP keyword matches for header row
    continuation_max_occupancy: float = 0.4   # Max row2 fill ratio for continuation
    continuation_max_cell_len: int = 30       # Max cell length in a continuation row
    generic_header_reuse_threshold: float = 0.5  # Reuse prev headers if generic% > this

    # ── Metadata table ────────────────────────────────────────────────
    metadata_max_cols: int = 5
    metadata_max_rows: int = 8
    metadata_max_cell_len: int = 80
    metadata_min_strong_keys: int = 2  # Required strong key matches (or 1 strong + 1 context)

    # ── Section heading ───────────────────────────────────────────────
    section_max_data_keys: int = 2
    section_max_text_len: int = 80

    # ── Quality scoring weights ───────────────────────────────────────
    quality_weight_field_count: float = 0.25
    quality_weight_text_length: float = 0.25
    quality_weight_has_context: float = 0.20
    quality_weight_has_procedure_no: float = 0.15
    quality_weight_no_generic: float = 0.15

    # ── Deduplication ─────────────────────────────────────────────────
    dedup_similarity_threshold: float = 0.90  # Jaccard threshold for near-dup detection

    # ── Cross-page merging ────────────────────────────────────────────
    cross_page_header_match_ratio: float = 0.6  # Min header overlap to consider same table

    # ── Column type confidence ────────────────────────────────────────
    col_type_min_confidence: float = 0.40  # Min confidence to accept statistical type



# ═══════════════════════════════════════════════════════════════════════
#  Column Type Detection Patterns
# ═══════════════════════════════════════════════════════════════════════

_COL_PATTERNS: Dict[str, Any] = {
    'no': {
        'regex': re.compile(r'^\d+(\.\d+){1,3}$'),
        'max_len': 15,
    },
    'procedures': {
        'min_len': 60,
    },
    'control': {
        'starts': ('ensure', 'to ensure', 'verify', 'to verify', 'confirm',
                   'maintain', 'to maintain', 'to safeguard', 'to prevent', 'to protect'),
    },
    'control_owner': {
        'keywords': ['cto', 'cio', 'ciso', 'cso', 'cfo', 'ceo', 'manager',
                     'head of', 'officer', 'director', 'dm ', 'senior',
                     'executive', 'hr', 'admin'],
        'max_len': 50,
    },
    'channel': {
        'values': {'email', 'phone', 'meeting', 'letter', 'portal', 'system', 'verbal',
                   'memo', 'report', 'presentation', 'intranet'},
    },
    'document': {
        'regex': re.compile(r'^[A-Z]{2,5}[-/][A-Z]?\d'),
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  Main Processor Class
# ═══════════════════════════════════════════════════════════════════════

class StructuredJSONProcessor:
    """
    Process structured/tabular documents as JSON objects.
    Suitable for manuals, procedures, forms, and tabular data.

    Advanced capabilities:
    - Removes empty columns; merges misaligned column pairs
    - Detects metadata vs. procedure tables
    - Smart multi-row header extraction with cross-page reuse
    - Section heading detection and context propagation
    - Hierarchical procedure grouping
    - Chunk quality scoring and near-duplicate removal
    - Statistical column type refinement
    - Configurable via ProcessorConfig
    """

    # ── Known SOP header patterns (order matters: specific before general) ──
    SOP_HEADER_PATTERNS = {
        'no': ['no', 'no.', 'number', '#', 'step', 'item', 's/n', 'sr', 'sr.'],
        'procedures': ['procedures', 'procedure', 'process', 'activity',
                       'description', 'action', 'task', 'steps'],
        'control_owner': ['control owner', 'owner', 'responsible',
                          'responsible party', 'assigned to', 'accountable'],
        'control': ['control', 'control objective', 'objective',
                    'control description'],
        'channel': ['channel', 'communication', 'medium',
                    'communication channel', 'comm channel'],
        'document': ['document', 'reference', 'ref', 'reference document',
                     'doc', 'supporting document', 'evidence'],
    }

    # Strong metadata keys for table classification
    _STRONG_METADATA_KEYS = [
        'document no', 'version no', 'issued date', 'effective from',
        'effective date', 'revision', 'prepared by', 'approved by',
        'reviewed by', 'version number', 'doc no', 'document number',
        'revision no', 'revision date', 'page', 'classification',
    ]

    # Context keywords for metadata table classification
    _CONTEXT_KEYWORDS = ['manual', 'department', 'sop', 'policy', 'standard',
                         'guideline', 'directive']

    # Section heading keywords
    _SECTION_KEYWORDS = [
        'security', 'access', 'management', 'procedure', 'policy',
        'action', 'corrective', 'incident', 'network', 'software',
        'hardware', 'physical', 'backup', 'disaster', 'recovery',
        'monitoring', 'audit', 'compliance', 'overview', 'scope',
        'objective', 'purpose', 'responsibility', 'cctv', 'asset',
        'inventory', 'maintenance', 'training', 'awareness',
        'change management', 'risk', 'business continuity',
    ]

    # ── Header keyword universe (for repeat detection) ──
    _HEADER_WORDS: Set[str] = set()
    for _patterns in SOP_HEADER_PATTERNS.values():
        _HEADER_WORDS.update(_patterns)

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.cfg = config or ProcessorConfig()
        self._reset_state()

    def _reset_state(self):
        """Reset all per-document state."""
        self._seen_headers: Set[tuple] = set()
        self._document_context: Dict[str, str] = {}
        self._current_section: Optional[str] = None
        self._last_known_headers: Optional[List[str]] = None
        self._prev_page_table_headers: Optional[List[str]] = None
        self._prev_page_pending_rows: List[List] = []
        self._procedure_hierarchy: Dict[str, str] = {}  # child_no → parent_section

    # ═══════════════════════════════════════════════════════════════════
    #  Public API
    # ═══════════════════════════════════════════════════════════════════

    def process_json_file(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """Process a JSON file containing structured data."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError("JSON must contain an object or array of objects")

        chunks = [self._create_structured_chunk(item, doc_id, filename, idx)
                  for idx, item in enumerate(data)]
        return chunks, doc_id, len(data)

    def process_csv_file(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """Process a CSV file as structured data."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        df = pd.read_csv(file_path)
        data = df.to_dict('records')

        chunks = [self._create_structured_chunk(item, doc_id, filename, idx)
                  for idx, item in enumerate(data)]
        return chunks, doc_id, len(data)

    def extract_tables_from_docx(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """
        Extract tables from a .docx file \u2192 structured JSON chunks.

        Uses python-docx to read tables, deduplicates merged cells,
        then runs the same pipeline as extract_tables_from_pdf.
        """
        try:
            from docx import Document as DocxDocument
        except ImportError as exc:
            raise ImportError(
                "python-docx is required for DOCX processing: "
                "pip install python-docx"
            ) from exc

        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        self._reset_state()

        docx_doc = DocxDocument(file_path)

        # Pull document-level metadata from core properties
        try:
            props = docx_doc.core_properties
            if props.title:
                self._document_context['title'] = props.title
            if props.subject:
                self._document_context['subject'] = props.subject
        except Exception:
            pass

        structured_data: List[Dict[str, Any]] = []

        for table_idx, table in enumerate(docx_doc.tables):
            try:
                raw_table: List[List[str]] = [
                    [cell.text.strip() for cell in row.cells]
                    for row in table.rows
                ]
                # Deduplicate cells repeated by merged-cell artefacts
                raw_table = self._deduplicate_docx_row_cells(raw_table)
                if len(raw_table) < 2:
                    continue
                table_items = self._process_single_table(
                    raw_table, page_num=1, table_idx=table_idx
                )
                structured_data.extend(table_items)
            except Exception as e:
                logger.warning(
                    "Error processing table %d in %s: %s",
                    table_idx, filename, e, exc_info=True
                )
                continue

        chunks = [
            self._create_structured_chunk(item, doc_id, filename, idx)
            for idx, item in enumerate(structured_data)
        ]
        chunks = self._merge_small_chunks(chunks)
        chunks = self._deduplicate_chunks(chunks)

        for idx, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = idx
            chunk['metadata']['total_chunks'] = len(chunks)
            chunk['metadata']['quality_score'] = self._score_chunk_quality(chunk)

        logger.info(
            "DOCX structured processing: %d chunks from %d table rows (%s)",
            len(chunks), len(structured_data), filename
        )
        return chunks, doc_id, len(chunks)

    @staticmethod
    def _deduplicate_docx_row_cells(table: List[List[str]]) -> List[List[str]]:
        """
        python-docx repeats the same cell text for every column a merged cell
        spans. Strip those adjacent duplicates so the table looks like a normal
        grid and the header/column-count logic works correctly.
        """
        result: List[List[str]] = []
        for row in table:
            deduped: List[str] = []
            prev: object = object()  # unique sentinel
            for cell in row:
                if cell != prev:
                    deduped.append(cell)
                prev = cell
            result.append(deduped)

        if not result:
            return result

        # Pad all rows to the same width
        max_len = max(len(r) for r in result)
        return [r + [''] * (max_len - len(r)) for r in result]

    def extract_tables_from_pdf(
        self,
        file_path: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """
        Extract tables from PDF → structured JSON chunks.

        Pipeline:
        1. Per-page table extraction (line-based → fallback text-based)
        2. Empty column removal
        3. Misaligned column merging
        4. Cross-page table continuity
        5. Metadata vs procedure classification
        6. Smart header extraction (multi-row, reuse)
        7. Statistical column typing
        8. Section heading detection
        9. Data row → item dict
        10. Chunk creation with quality scores
        11. Small-chunk merging + near-duplicate removal
        12. Hierarchical procedure linking
        """
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        self._reset_state()

        structured_data: List[Dict[str, Any]] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_items = self._process_page(page, page_num)
                        structured_data.extend(page_items)
                    except Exception as e:
                        logger.error("Error processing page %d of %s: %s",
                                     page_num, filename, e, exc_info=True)
                        continue
        except Exception as e:
            logger.error("Failed to open PDF %s: %s", filename, e, exc_info=True)
            return [], doc_id, 0

        # ── Post-processing pipeline ──
        chunks = [self._create_structured_chunk(item, doc_id, filename, idx)
                  for idx, item in enumerate(structured_data)]

        # Merge tiny chunks
        chunks = self._merge_small_chunks(chunks)

        # Near-duplicate removal
        chunks = self._deduplicate_chunks(chunks)

        # Re-index + quality score
        for idx, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = idx
            chunk['metadata']['total_chunks'] = len(chunks)
            chunk['metadata']['quality_score'] = self._score_chunk_quality(chunk)

        logger.info("Structured processing: %d chunks from %d table rows (%s)",
                     len(chunks), len(structured_data), filename)
        return chunks, doc_id, len(chunks)

    # ═══════════════════════════════════════════════════════════════════
    #  Per-page Processing
    # ═══════════════════════════════════════════════════════════════════

    def _process_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract and process all tables from a single PDF page."""
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 4,
            "join_tolerance": 4,
            "edge_min_length": 3,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
        })

        if not tables:
            tables = page.extract_tables()

        if not tables:
            return []

        items: List[Dict[str, Any]] = []
        for table_idx, table in enumerate(tables):
            try:
                table_items = self._process_single_table(table, page_num, table_idx)
                items.extend(table_items)
            except Exception as e:
                logger.warning("Error processing table %d on page %d: %s",
                               table_idx, page_num, e, exc_info=True)
                continue
        return items

    def _process_single_table(
        self, table: List[List], page_num: int, table_idx: int
    ) -> List[Dict[str, Any]]:
        """Full pipeline for one raw table."""
        if not table or len(table) < 2:
            return []

        # Step 1: Remove empty columns
        table = self._remove_empty_columns(table)
        if not table or len(table) < 2:
            return []

        # Step 2: Merge misaligned columns
        table = self._merge_misaligned_columns(table)
        if not table or len(table) < 2:
            return []

        # Step 3: Cross-page continuity
        table = self._handle_cross_page_continuity(table, page_num)
        if not table or len(table) < 2:
            return []

        # Step 4: Metadata table detection
        if self._is_metadata_table(table):
            metadata = self._extract_document_metadata(table)
            self._document_context.update(metadata)
            logger.info("Page %d: Metadata table detected: %s", page_num, metadata)
            return []

        # Step 5: Extract smart headers
        headers, header_rows_count = self._extract_smart_headers(table)

        # Step 6: Repeated header check
        header_sig = tuple(h for h in headers if h)
        if header_sig in self._seen_headers and page_num > 1:
            logger.debug("Page %d: Skipping repeated header row", page_num)
        else:
            self._seen_headers.add(header_sig)

        # Step 7: Reuse last known good headers if current are mostly generic
        generic_count = sum(1 for h in headers if h.startswith('field_'))
        if generic_count > len(headers) * self.cfg.generic_header_reuse_threshold:
            if self._last_known_headers and len(self._last_known_headers) == len(headers):
                logger.debug("Page %d: Reusing previous headers (too many generic)", page_num)
                headers = self._last_known_headers

        if generic_count <= len(headers) * 0.3:
            self._last_known_headers = headers

        # Step 8: Statistical column type refinement
        headers = self._refine_headers_statistically(headers, table[header_rows_count:])

        # Store for cross-page continuity
        self._prev_page_table_headers = headers

        # Step 9: Process data rows
        raw_data_rows = table[header_rows_count:]

        items: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(raw_data_rows):
                if not any(str(cell).strip() for cell in row if cell):
                    continue

                if self._is_header_repeat(row, headers):
                    continue

                item = self._row_to_item(row, headers)
                if not item:
                    continue

                # Extract 'Performed by' embedded in procedure text (regex fallback)
                for proc_key in ('procedures', 'procedure', 'process', 'description', 'activity'):
                    if proc_key in item and 'performed_by' not in item:
                        cleaned, pb = self._extract_performed_by(item[proc_key])
                        if pb:
                            item[proc_key] = cleaned
                            item['performed_by'] = pb
                        break

                # Section heading detection
                if self._is_section_heading_row(item, headers):
                    section_title = self._extract_section_title(item)
                    if section_title:
                        self._current_section = section_title
                        logger.debug("Page %d: Section heading: %s",
                                     page_num, section_title)
                    continue

                # Enrich with metadata
                item['_source_page'] = page_num
                item['_table_index'] = table_idx
                item['_row_index'] = row_idx
                if self._document_context:
                    item['_document_context'] = self._document_context.copy()
                if self._current_section:
                    item['_section'] = self._current_section

                proc_no = item.get('no', '')
                if self._current_section and proc_no:
                    self._procedure_hierarchy[proc_no] = self._current_section

                data_keys = [k for k in item if not k.startswith('_')]
                if len(data_keys) >= 2:
                    items.append(item)

        return items

    def _REMOVED_llm_repair_table(
        self,
        headers: List[str],
        data_rows: List[List],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Send raw PDF-extracted table rows to the LLM for repair.

        Fixes automatically:
        - TEXT BLEED: sentence fragments from adjacent rows bleeding into a cell
        - TRUNCATION: sentences cut off mid-way due to narrow PDF columns
        - DUPLICATE CONTENT: same data appearing in two fields

        Returns cleaned list of row-dicts, or None if repair not available / failed.
        Caller must fall back to raw row processing on None.
        """
        if not self.cfg.enable_llm_repair or self._llm is None or not data_rows:
            return None

        # Build minimal readable representation — only non-empty, non-neutral cells
        raw_rows: List[Dict[str, str]] = []
        for row in data_rows:
            row_dict: Dict[str, str] = {}
            for h, cell in zip(headers, row):
                val = str(cell).strip() if cell else ''
                if h and val and val.lower() not in self._NEUTRAL_VALUES:
                    row_dict[h] = val
            if row_dict:
                raw_rows.append(row_dict)

        if not raw_rows:
            return None

        col_desc = ', '.join(f'"{h}"' for h in headers if h)
        prompt = (
            "You are a precise PDF table repair tool.\n\n"
            "The rows below were extracted from a PDF SOP table using pdfplumber. "
            "Fix ALL of these common PDF extraction errors you find:\n"
            "1. TEXT BLEED — a sentence fragment from a different row got "
            "concatenated into a cell (e.g. the cell ends with a complete sentence "
            "then starts an unrelated new sentence — remove the unrelated part).\n"
            "2. TRUNCATION — a cell ends mid-sentence because the PDF column was "
            "too narrow. Complete it only when obviously deducible from context; "
            "otherwise leave as-is.\n"
            "3. DUPLICATE CONTENT — the same information appears in two fields; "
            "keep it only in the most appropriate field.\n"
            "4. PERFORMED BY EXTRACTION — if a procedure/description cell contains "
            "a phrase like 'Performed by: X', extract that value into a separate "
            '"performed_by" field and remove it from the procedure text.\n'
            "5. MISSING CONTROL OBJECTIVE — if the control_objective / control field "
            "is absent or empty, infer a concise one-sentence objective starting with "
            "'To ensure…' from the procedure text. If you cannot infer it "
            "confidently, omit it.\n"
            "6. TOPIC TAGS — add a \"topic_tags\" field: a JSON array of 1-3 short "
            "readable keyword phrases that best categorise this procedure "
            '(e.g. ["asset management", "physical security"]).\n\n'
            f"Column names (use these exact strings as JSON keys): {col_desc}\n"
            'You may also add: "performed_by" (string), "topic_tags" (array).\n\n'
            "Raw extracted rows:\n"
            f"{json.dumps(raw_rows, indent=2, ensure_ascii=False)}\n\n"
            "Return ONLY a valid JSON object — no explanation, no markdown:\n"
            '{"rows": [{...}, ...]}\n\n'
            "Rules:\n"
            "- Use the exact column name strings as keys (plus performed_by / topic_tags as needed)\n"
            "- Omit keys whose value is N/A, -, nil, none, or empty\n"
            "- Return ALL rows (even unchanged ones)\n"
            "- Do NOT invent information beyond what instructions 4-6 explicitly allow"
        )

        try:
            from langchain_core.messages import HumanMessage
            response = self._llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # Strip markdown code fences that some models add
            content = re.sub(r'^```[a-zA-Z]*\n?', '', content)
            content = re.sub(r'\n?```$', '', content.strip())

            parsed = json.loads(content)
            rows = parsed.get('rows', [])
            if isinstance(rows, list) and rows:
                logger.debug("LLM repaired %d table rows", len(rows))
                return rows
            return None

        except Exception as exc:
            logger.warning("LLM table repair failed — falling back to raw extraction: %s", exc)
            return None

    @staticmethod
    def _extract_performed_by(procedure_text: str) -> Tuple[str, Optional[str]]:
        """
        Detect 'Performed by: X' in procedure text, extract the value,
        and return (cleaned_text_without_it, performed_by_value).
        Returns (original_text, None) when the pattern is absent.
        """
        pattern = re.compile(
            r'[.\s]*[Pp]erformed\s+[Bb]y\s*:\s*([^\n.;]{2,80})',
            re.IGNORECASE,
        )
        match = pattern.search(procedure_text)
        if match:
            performed_by = match.group(1).strip().rstrip('.')
            cleaned = pattern.sub('', procedure_text).strip()
            return cleaned, performed_by
        return procedure_text, None

    @staticmethod
    def _row_to_item(row: List, headers: List[str]) -> Dict[str, Any]:
        """Convert a raw table row + headers into a cleaned item dict."""
        item: Dict[str, Any] = {}
        for header, cell in zip(headers, row):
            if cell and str(cell).strip() and header:
                clean_val = ' '.join(str(cell).strip().split())
                item[header] = clean_val
        return item

    # ═══════════════════════════════════════════════════════════════════
    #  Cross-Page Table Continuity
    # ═══════════════════════════════════════════════════════════════════

    def _handle_cross_page_continuity(
        self, table: List[List], page_num: int
    ) -> List[List]:
        """
        If first table on a new page looks like a continuation of the
        previous page's table (same column count, repeated header row),
        strip the duplicate header.
        """
        if page_num <= 1 or self._prev_page_table_headers is None:
            return table

        prev_headers = self._prev_page_table_headers
        curr_cols = len(table[0]) if table else 0
        prev_cols = len(prev_headers)

        if curr_cols != prev_cols:
            return table

        first_row = table[0]
        first_cells = [str(c).strip().lower() if c else '' for c in first_row]
        non_empty_first = [c for c in first_cells if c]

        if not non_empty_first:
            return table

        matches = sum(1 for c in non_empty_first
                      if c.rstrip('.') in self._HEADER_WORDS)
        match_ratio = matches / len(non_empty_first) if non_empty_first else 0

        if match_ratio >= self.cfg.cross_page_header_match_ratio:
            logger.debug("Page %d: Stripped continuation header row", page_num)
            table = table[1:]

        return table

    # ═══════════════════════════════════════════════════════════════════
    #  Column Operations
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _remove_empty_columns(table: List[List]) -> List[List]:
        """Remove columns that are entirely empty."""
        if not table:
            return table

        num_cols = max(len(row) for row in table)
        normalized = [list(row) + [None] * (num_cols - len(row)) for row in table]

        cols_with_content = [
            col_idx for col_idx in range(num_cols)
            if any(row[col_idx] and str(row[col_idx]).strip() for row in normalized)
        ]

        if not cols_with_content:
            return []

        return [[row[i] for i in cols_with_content] for row in normalized]

    def _merge_misaligned_columns(self, table: List[List]) -> List[List]:
        """
        Fix column misalignment from PDF merged cells.

        When header cells span different physical columns than data cells,
        pdfplumber creates adjacent columns where one has header text and
        the other has data text. This detects and merges such complementary pairs.
        """
        if not table or len(table) < 2:
            return table

        num_cols = len(table[0])
        if num_cols <= self.cfg.merge_column_threshold:
            return table

        # Analyse header vs data content distribution per column
        header_rows_est = min(2, len(table))
        header_part = table[:header_rows_est]
        data_part = table[header_rows_est:]

        col_header_fill = [
            any(i < len(row) and row[i] and str(row[i]).strip()
                for row in header_part)
            for i in range(num_cols)
        ]
        col_data_fill = [
            any(i < len(row) and row[i] and str(row[i]).strip()
                for row in data_part)
            for i in range(num_cols)
        ]

        # Build merge pairs (dict for O(1) lookup)
        merge_pairs: Dict[int, int] = {}
        i = 0
        while i < num_cols - 1:
            a_h, a_d = col_header_fill[i], col_data_fill[i]
            b_h, b_d = col_header_fill[i + 1], col_data_fill[i + 1]

            is_complementary = (
                (a_d and not a_h and b_h and not b_d) or
                (a_h and not a_d and b_d and not b_h)
            )

            if not is_complementary and (a_h or a_d) and (b_h or b_d):
                both_count = sum(
                    1 for row in table
                    if (i < len(row) and row[i] and str(row[i]).strip()) and
                       (i + 1 < len(row) and row[i + 1] and str(row[i + 1]).strip())
                )
                if len(table) > 0 and both_count / len(table) < self.cfg.merge_overlap_ratio:
                    is_complementary = True

            if is_complementary:
                merge_pairs[i] = i + 1
                i += 2
            else:
                i += 1

        if not merge_pairs:
            return table

        logger.debug("Merging %d misaligned column pairs: %s",
                      len(merge_pairs), list(merge_pairs.items()))

        result = []
        for row in table:
            new_row = []
            i = 0
            while i < num_cols:
                if i in merge_pairs:
                    cell_a = row[i] if i < len(row) else None
                    cell_b = row[i + 1] if i + 1 < len(row) else None
                    has_a = cell_a and str(cell_a).strip()
                    has_b = cell_b and str(cell_b).strip()

                    if has_a and has_b:
                        new_row.append(str(cell_a).strip() + ' ' + str(cell_b).strip())
                    elif has_a:
                        new_row.append(cell_a)
                    elif has_b:
                        new_row.append(cell_b)
                    else:
                        new_row.append(None)
                    i += 2
                else:
                    new_row.append(row[i] if i < len(row) else None)
                    i += 1
            result.append(new_row)

        new_num = len(result[0]) if result else 0
        logger.debug("Columns reduced: %d → %d", num_cols, new_num)
        return result

    # ═══════════════════════════════════════════════════════════════════
    #  Header Detection
    # ═══════════════════════════════════════════════════════════════════

    def _extract_smart_headers(self, table: List[List]) -> Tuple[List[str], int]:
        """Extract meaningful headers, handling merged cells and multi-row headers."""
        if not table:
            return [], 0

        first_row = table[0]

        if not self._row_looks_like_header(first_row):
            headers = self._infer_headers_from_data(table)
            return headers, 0

        raw_headers = [str(h).strip() if h else '' for h in first_row]

        header_rows = 1
        if len(table) > 2:
            second_row = table[1]
            second_cells = [str(c).strip() if c else '' for c in second_row]

            if self._is_header_continuation(raw_headers, second_cells):
                merged = []
                for h1, h2 in zip(raw_headers, second_cells):
                    if h1 and h2:
                        merged.append(f"{h1} {h2}")
                    elif h1:
                        merged.append(h1)
                    else:
                        merged.append(h2)
                raw_headers = merged
                header_rows = 2

        headers = self._map_headers_to_fields(raw_headers)
        return headers, header_rows

    def _row_looks_like_header(self, row: List) -> bool:
        """Check if a row looks like table headers."""
        if not row:
            return False

        cells = [str(c).strip() if c else '' for c in row]
        non_empty = [c for c in cells if c]
        if not non_empty:
            return False

        avg_len = sum(len(c) for c in non_empty) / len(non_empty)
        if avg_len > self.cfg.header_max_avg_len:
            return False

        if any(re.match(r'^\d+\.\d+\.\d+', c) for c in non_empty):
            return False

        header_keywords = [
            'no', 'number', 'procedure', 'control', 'owner', 'channel',
            'document', 'description', 'action', 'step', 'reference',
            'responsible', 'status', 'date', 'frequency',
        ]
        all_text = ' '.join(non_empty).lower()
        keyword_hits = sum(1 for kw in header_keywords if kw in all_text)

        return keyword_hits >= self.cfg.header_min_keyword_hits or avg_len < 25

    def _is_header_continuation(self, row1: List[str], row2: List[str]) -> bool:
        """
        Check if row2 is a continuation of headers from row1.

        Detects:
        1. Gap-fill: row1 empty, row2 fills it
        2. Append: row2 adds a word to row1 (e.g. 'Control' + 'Owner')

        Key distinction: continuation rows are mostly empty.
        """
        non_empty_r2 = [c for c in row2 if c and c.strip()]
        if not non_empty_r2:
            return False

        total_cols = len(row2)
        if total_cols > 0 and len(non_empty_r2) > max(2, total_cols * self.cfg.continuation_max_occupancy):
            return False

        fills_gaps = 0
        continues_header = 0

        for h1, h2 in zip(row1, row2):
            h2_clean = h2.strip() if h2 else ''
            h1_clean = h1.strip() if h1 else ''

            if not h1_clean and h2_clean and len(h2_clean) < self.cfg.continuation_max_cell_len:
                fills_gaps += 1
            elif h1_clean and h2_clean and len(h2_clean) < 25:
                continues_header += 1

        avg_len = sum(len(c.strip()) for c in non_empty_r2) / len(non_empty_r2)
        return avg_len < self.cfg.continuation_max_cell_len and (fills_gaps + continues_header) >= 1

    def _map_headers_to_fields(self, raw_headers: List[str]) -> List[str]:
        """Map raw header text to standardised field names."""
        mapped = []
        used_names: Set[str] = set()

        for header in raw_headers:
            if not header:
                mapped.append('')
                continue

            header_lower = header.lower().strip().rstrip('.')
            matched_field = None

            # Pass 1: Exact match
            for field_name, patterns in self.SOP_HEADER_PATTERNS.items():
                if header_lower in patterns:
                    matched_field = field_name
                    break

            # Pass 2: Containment match
            if not matched_field:
                for field_name, patterns in self.SOP_HEADER_PATTERNS.items():
                    if any(p in header_lower for p in patterns):
                        matched_field = field_name
                        break

            if matched_field:
                final_name = matched_field
                counter = 1
                while final_name in used_names:
                    final_name = f"{matched_field}_{counter}"
                    counter += 1
                used_names.add(final_name)
                mapped.append(final_name)
            else:
                clean = self._clean_header(header)
                if clean:
                    final_name = clean
                    counter = 1
                    while final_name in used_names:
                        final_name = f"{clean}_{counter}"
                        counter += 1
                    used_names.add(final_name)
                    mapped.append(final_name)
                else:
                    mapped.append('')

        return mapped

    # ═══════════════════════════════════════════════════════════════════
    #  Statistical Column Typing
    # ═══════════════════════════════════════════════════════════════════

    def _refine_headers_statistically(
        self, headers: List[str], data_rows: List[List]
    ) -> List[str]:
        """
        Refine generic 'field_N' headers using statistical analysis
        of ALL data rows (not just first 5).

        For each generic column, count how many rows match each column-type
        pattern. If a type exceeds the confidence threshold, apply it.
        """
        if not data_rows:
            return headers

        refined = list(headers)
        used = set(h for h in headers if not h.startswith('field_'))
        num_rows = len(data_rows)

        for col_idx, header in enumerate(headers):
            if not header.startswith('field_'):
                continue

            values = []
            for row in data_rows:
                if col_idx < len(row) and row[col_idx]:
                    val = str(row[col_idx]).strip()
                    if val:
                        values.append(val)

            if not values:
                continue

            type_scores: Dict[str, float] = {}
            for type_name, pattern_info in _COL_PATTERNS.items():
                if type_name in used:
                    continue
                score = self._score_column_type(values, type_name, pattern_info)
                if score > 0:
                    type_scores[type_name] = score

            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                best_score = type_scores[best_type]

                if best_score >= self.cfg.col_type_min_confidence:
                    refined[col_idx] = best_type
                    used.add(best_type)
                    logger.debug("Column %d: '%s' → '%s' (confidence: %.2f)",
                                 col_idx, header, best_type, best_score)

        return refined

    # Values that are ambiguous placeholders — exclude from scoring denominator
    _NEUTRAL_VALUES = {'n/a', 'na', '-', 'none', '', 'nil', 'tbd', 'tba'}

    @staticmethod
    def _score_column_type(
        values: List[str], type_name: str, pattern_info: Dict
    ) -> float:
        """Score how well a list of values matches a column type pattern.
        
        Ambiguous placeholders (N/A, -, None) are excluded from scoring
        so they don't dilute confidence for columns that have them.
        """
        if not values:
            return 0.0

        # Filter out neutral/placeholder values
        scorable = [v for v in values if v.lower().strip() not in
                    StructuredJSONProcessor._NEUTRAL_VALUES]
        if not scorable:
            return 0.0

        matches = 0
        for val in scorable:
            val_lower = val.lower().strip()

            if 'regex' in pattern_info and pattern_info['regex'].match(val):
                if 'max_len' in pattern_info and len(val) > pattern_info['max_len']:
                    continue
                matches += 1
            elif 'min_len' in pattern_info and len(val) >= pattern_info['min_len']:
                matches += 1
            elif 'starts' in pattern_info and val_lower.startswith(pattern_info['starts']):
                matches += 1
            elif 'keywords' in pattern_info:
                max_len = pattern_info.get('max_len', 9999)
                if len(val) <= max_len and any(kw in val_lower for kw in pattern_info['keywords']):
                    matches += 1
            elif 'values' in pattern_info and val_lower in pattern_info['values']:
                matches += 1

        return matches / len(scorable)

    # ═══════════════════════════════════════════════════════════════════
    #  Header Inference (no header row)
    # ═══════════════════════════════════════════════════════════════════

    def _infer_headers_from_data(self, table: List[List]) -> List[str]:
        """
        Infer column headers from data patterns when no header row is present.

        Strategy:
        1. Detect specific patterns (procedure numbers, channels, etc.)
        2. If col 0 is 'no', apply SOP positional heuristics
        3. Fill remaining with generic field names
        """
        if not table:
            return []

        num_cols = len(table[0])
        inferred = [''] * num_cols

        SOP_COLUMN_ORDER = ['no', 'procedures', 'control',
                            'control_owner', 'channel', 'document']

        # Phase 1: Pattern-based detection from sample rows
        for row in table[:5]:
            for col_idx, cell in enumerate(row):
                if not cell or col_idx >= num_cols:
                    continue
                val = str(cell).strip()
                val_lower = val.lower()

                if re.match(r'^\d+\.\d+(\.\d+)?$', val):
                    inferred[col_idx] = 'no'
                elif len(val) > 80 and not inferred[col_idx]:
                    inferred[col_idx] = 'procedures'
                elif val_lower in {'email', 'phone', 'meeting', 'letter', 'portal'}:
                    inferred[col_idx] = 'channel'
                elif val_lower.startswith(('ensure', 'to ensure', 'verify', 'to verify', 'maintain')):
                    if not inferred[col_idx]:
                        inferred[col_idx] = 'control'

        # Phase 2: SOP positional defaults if col 0 is 'no'
        if inferred[0] == 'no' and num_cols <= len(SOP_COLUMN_ORDER) + 2:
            for i in range(num_cols):
                if not inferred[i] and i < len(SOP_COLUMN_ORDER):
                    inferred[i] = SOP_COLUMN_ORDER[i]

        # Phase 3: Fill remaining gaps
        for i in range(num_cols):
            if not inferred[i]:
                inferred[i] = f'field_{i + 1}'

        return inferred

    # ═══════════════════════════════════════════════════════════════════
    #  Table Classification
    # ═══════════════════════════════════════════════════════════════════

    def _is_metadata_table(self, table: List[List]) -> bool:
        """Detect if a table is a document metadata/header table."""
        if not table or len(table) < 2:
            return False

        num_cols = max(len(row) for row in table)
        col_has_data = set()
        for row in table:
            for i, c in enumerate(row):
                if c and str(c).strip():
                    col_has_data.add(i)

        if len(col_has_data) > self.cfg.metadata_max_cols or len(table) > self.cfg.metadata_max_rows:
            return False

        all_cells = [str(cell).strip() for row in table
                     for cell in row if cell and str(cell).strip()]

        for cell_text in all_cells:
            if re.match(r'^\d+\.\d+\.\d+', cell_text):
                return False
            if len(cell_text) > self.cfg.metadata_max_cell_len:
                return False

        all_text_lower = ' '.join(all_cells).lower()
        strong = sum(1 for kw in self._STRONG_METADATA_KEYS if kw in all_text_lower)
        context = sum(1 for kw in self._CONTEXT_KEYWORDS if kw in all_text_lower)

        return (strong >= 1 and context >= 1) or strong >= self.cfg.metadata_min_strong_keys

    def _extract_document_metadata(self, table: List[List]) -> Dict[str, str]:
        """Extract key-value metadata from a document header table."""
        metadata: Dict[str, str] = {}

        for row in table:
            cells = [str(c).strip() if c else '' for c in row]
            non_empty = [c for c in cells if c]
            if not non_empty:
                continue

            first_cell = cells[0].lower() if cells[0] else ''

            if any(kw in first_cell for kw in ['department', 'information technology', 'it dept', 'manual']):
                if 'information technology' in first_cell or 'department' in first_cell:
                    metadata.setdefault('department', cells[0])

                remaining = [c for c in cells[1:] if c]
                if len(remaining) >= 2:
                    self._map_metadata_kv(remaining[0], remaining[1], metadata)
                elif len(remaining) == 1:
                    self._map_metadata_kv(first_cell, remaining[0], metadata)
            elif len(non_empty) >= 2:
                self._map_metadata_kv(non_empty[0], non_empty[1], metadata)
                if len(non_empty) >= 4:
                    self._map_metadata_kv(non_empty[2], non_empty[3] if len(non_empty) > 3 else '', metadata)

        return metadata

    def _map_metadata_kv(self, key: str, value: str, metadata: Dict[str, str]):
        """Map a key-value pair to the appropriate metadata field."""
        key_lower = key.lower().strip().rstrip(':')
        value = value.strip()

        if not key_lower or not value or len(value) > self.cfg.metadata_max_cell_len:
            return

        _MAPPING = [
            (['document no', 'doc no', 'document number'], 'document_no'),
            (['version no', 'version number'], 'version'),
            (['version'], 'version'),
            (['issued', 'issue date'], 'issued_date'),
            (['effective'], 'effective_date'),
            (['title'], 'title'),
            (['prepared', 'author'], 'prepared_by'),
            (['approved'], 'approved_by'),
            (['revision'], 'revision'),
            (['department'], 'department'),
            (['manual'], 'manual'),
            (['classification'], 'classification'),
        ]

        for keywords, field_name in _MAPPING:
            if any(k in key_lower for k in keywords):
                if field_name == 'manual':
                    metadata.setdefault(field_name, value)
                else:
                    metadata[field_name] = value
                return

        clean_key = self._clean_header(key_lower)
        if clean_key and value:
            metadata[clean_key] = value

    # ═══════════════════════════════════════════════════════════════════
    #  Section & Row Detection
    # ═══════════════════════════════════════════════════════════════════

    def _is_section_heading_row(self, item: Dict[str, Any], headers: List[str]) -> bool:
        """Detect section heading rows within tables."""
        if not item:
            return False

        data_keys = [k for k in item if not k.startswith('_')]
        if len(data_keys) > self.cfg.section_max_data_keys:
            return False

        all_text = ' '.join(str(item[k]) for k in data_keys).strip()
        if not all_text or len(all_text) < 3 or len(all_text) > self.cfg.section_max_text_len:
            return False

        if re.match(r'^\d+\.\d+', all_text):
            return False

        is_title_case = all_text == all_text.title() or all_text == all_text.upper()
        has_section_words = any(w in all_text.lower() for w in self._SECTION_KEYWORDS)

        return is_title_case or has_section_words

    def _extract_section_title(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract section title text from a heading row."""
        data_keys = [k for k in item if not k.startswith('_')]
        values = [str(item[k]).strip() for k in data_keys if item[k]]
        return max(values, key=len) if values else None

    def _is_header_repeat(self, row: List, headers: List[str]) -> bool:
        """Check if a data row is actually a repeated header row."""
        if not row or not headers:
            return False

        cells = [str(c).strip().lower() if c else '' for c in row]
        non_empty = [c for c in cells if c]

        if not non_empty:
            return True

        matches = sum(1 for c in non_empty if c.rstrip('.') in self._HEADER_WORDS)
        return matches >= 2 and matches >= len(non_empty) * 0.5

    # ═══════════════════════════════════════════════════════════════════
    #  Chunk Creation + Text Generation
    # ═══════════════════════════════════════════════════════════════════

    def _create_structured_chunk(
        self,
        item: Dict[str, Any],
        doc_id: str,
        filename: str,
        index: int
    ) -> Dict[str, Any]:
        """Create a searchable chunk from structured data."""
        text = self._json_to_searchable_text(item)

        metadata = {
            'document_id': doc_id,
            'filename': filename,
            'chunk_index': index,
            'chunk_type': 'structured',
            'procedure_no': (
                item.get('no') or item.get('procedure_no') or
                item.get('procedure_number') or item.get('step') or
                item.get('item')
            ),
            'section_id': item.get('section_id') or item.get('section'),
            'control_owner': (
                item.get('control_owner') or item.get('owner') or
                item.get('responsible')
            ),
            'applies_to': item.get('applies_to'),
            'group': item.get('group') or item.get('category'),
            'reference_doc': (
                item.get('document') or item.get('reference_doc') or
                item.get('reference')
            ),
            'channel': item.get('channel') or item.get('communication'),
            'status': item.get('status'),
            'source_page': item.get('_source_page'),
            'section': item.get('_section'),
            'performed_by': item.get('performed_by'),
            'topic_tags': item.get('topic_tags'),
            'structured_data': json.dumps(item, ensure_ascii=False),
        }

        # Hierarchical parent section
        proc_no = metadata.get('procedure_no')
        if proc_no and proc_no in self._procedure_hierarchy:
            metadata['parent_section'] = self._procedure_hierarchy[proc_no]

        metadata = {k: v for k, v in metadata.items() if v is not None}
        return {'text': text, 'metadata': metadata}

    # ── Field label mappings ──
    _FIELD_LABELS = {
        'no': 'Step/Procedure No.',
        'procedure_no': 'Procedure Number',
        'procedure_number': 'Procedure Number',
        'step': 'Step Number',
        'item': 'Item Number',
        'procedures': 'Procedure',
        'procedure': 'Procedure',
        'process': 'Process',
        'activity': 'Activity',
        'description': 'Description',
        'action': 'Action',
        'control': 'Control Objective',
        'control_objective': 'Control Objective',
        'objective': 'Objective',
        'control_owner': 'Control Owner',
        'owner': 'Owner',
        'responsible': 'Responsible Party',
        'responsible_party': 'Responsible Party',
        'performed_by': 'Performed By',
        'channel': 'Communication Channel',
        'communication': 'Communication Channel',
        'medium': 'Medium',
        'document': 'Reference Document',
        'reference_doc': 'Reference Document',
        'reference': 'Reference',
        'ref': 'Reference',
        'section_id': 'Section',
        'section_title': 'Section Title',
        'section': 'Section',
        'applies_to': 'Applies To',
        'group': 'Group',
        'category': 'Category',
        'status': 'Status',
        'content_type': 'Type',
        'frequency': 'Frequency',
        'deadline': 'Deadline',
        'sla': 'SLA',
        'performed_by': 'Performed By',
        'topic_tags': 'Topic Tags',
    }

    def _json_to_searchable_text(self, item: Dict[str, Any]) -> str:
        """Convert item dict to natural-language text for semantic search."""
        parts: List[str] = []
        internal = {'_source_page', '_table_index', '_row_index',
                     '_document_context', '_section'}

        # Document context header
        doc_ctx = item.get('_document_context', {})
        if doc_ctx:
            ctx = []
            if doc_ctx.get('document_no'):
                ctx.append(f"Document: {doc_ctx['document_no']}")
            if doc_ctx.get('department'):
                ctx.append(f"Department: {doc_ctx['department']}")
            if doc_ctx.get('version') and doc_ctx['version'] not in ('', 'N/A'):
                ctx.append(f"Version: {doc_ctx['version']}")
            if doc_ctx.get('title'):
                ctx.append(f"Title: {doc_ctx['title']}")
            if ctx:
                parts.append("[" + " | ".join(ctx) + "]")

        # Section + page context
        section = item.get('_section')
        source_page = item.get('_source_page')
        if section or source_page:
            line_parts = []
            if section:
                line_parts.append(f"Section: {section}")
            if source_page:
                line_parts.append(f"Page: {source_page}")
            parts.append(" | ".join(line_parts))

        # Data fields
        for key, value in item.items():
            if key in internal or not value:
                continue

            label = self._FIELD_LABELS.get(key, key.replace('_', ' ').title())
            if key.startswith('field_'):
                label = self._infer_field_label(key, str(value))

            if isinstance(value, (list, tuple)):
                value_str = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)

            # Skip neutral/placeholder values — don't pollute chunk text with N/A noise
            if value_str.strip().lower() in self._NEUTRAL_VALUES:
                continue

            # Also skip generic field_N keys that couldn't be resolved to a real label
            if key.startswith('field_') and label.startswith('Field '):
                continue

            if value_str.strip():
                if len(value_str) > 100:
                    parts.append(f"\n{label}:\n{value_str}")
                else:
                    parts.append(f"{label}: {value_str}")

        return "\n".join(parts)

    @staticmethod
    def _infer_field_label(field_key: str, value: str) -> str:
        """Infer a better label for generic field_N names based on value content."""
        val_lower = value.lower().strip()
        val_len = len(value.strip())

        if re.match(r'^\d+\.\d+(\.\d+)?$', val_lower):
            return 'Step/Procedure No.'

        if val_lower.startswith(('ensure', 'to ensure', 'verify', 'confirm',
                                 'maintain', 'to maintain', 'to safeguard',
                                 'to prevent', 'to protect')):
            return 'Control Objective'

        if val_len < 50:
            role_kw = ['cto', 'cio', 'ciso', 'cso', 'cfo', 'ceo', 'manager',
                       'head of', 'officer', 'director', 'dm ', 'senior',
                       'executive', 'hr']
            if any(kw in val_lower for kw in role_kw):
                return 'Control Owner'

        if val_lower in {'email', 'phone', 'meeting', 'letter', 'portal',
                         'system', 'verbal'}:
            return 'Communication Channel'

        if re.match(r'^[A-Z]{2,4}-[A-Z]?\d', value) or val_lower.startswith('itd-'):
            return 'Reference Document'

        if val_len > 80:
            return 'Procedure'

        if val_lower in {'n/a', 'na', '-', 'none', ''}:
            return field_key.replace('_', ' ').title()

        return field_key.replace('_', ' ').title()

    # ═══════════════════════════════════════════════════════════════════
    #  Chunk Quality Scoring
    # ═══════════════════════════════════════════════════════════════════

    def _score_chunk_quality(self, chunk: Dict[str, Any]) -> float:
        """
        Score chunk quality from 0.0 to 1.0 based on multiple signals.

        Signals:
        - Number of meaningful fields (more = better)
        - Text length (neither too short nor too long)
        - Has document context
        - Has procedure number
        - No generic field_N labels remain
        """
        text = chunk.get('text', '')
        meta = chunk.get('metadata', {})
        score = 0.0

        # Signal 1: Field count (target: 4-6 fields)
        structured = meta.get('structured_data', '{}')
        try:
            item = json.loads(structured)
            data_keys = [k for k in item if not k.startswith('_')]
            field_ratio = min(len(data_keys) / 6.0, 1.0)
        except (json.JSONDecodeError, TypeError):
            field_ratio = 0.0
        score += field_ratio * self.cfg.quality_weight_field_count

        # Signal 2: Text length (sweet spot: 100-800 chars)
        text_len = len(text)
        if text_len < 50:
            len_score = 0.1
        elif text_len < 100:
            len_score = 0.5
        elif text_len <= 800:
            len_score = 1.0
        elif text_len <= self.cfg.max_chunk_length:
            len_score = 0.8
        else:
            len_score = 0.5
        score += len_score * self.cfg.quality_weight_text_length

        # Signal 3: Has document context
        has_ctx = 1.0 if meta.get('section') or '[Document:' in text else 0.0
        score += has_ctx * self.cfg.quality_weight_has_context

        # Signal 4: Has procedure number
        has_proc = 1.0 if meta.get('procedure_no') else 0.0
        score += has_proc * self.cfg.quality_weight_has_procedure_no

        # Signal 5: No generic labels remain
        has_generic = 1.0 if 'Field ' not in text and 'field_' not in text else 0.0
        score += has_generic * self.cfg.quality_weight_no_generic

        return round(min(score, 1.0), 3)

    # ═══════════════════════════════════════════════════════════════════
    #  Deduplication
    # ═══════════════════════════════════════════════════════════════════

    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove near-duplicate chunks using Jaccard similarity on word sets.
        Keeps the first occurrence.
        """
        if len(chunks) <= 1:
            return chunks

        kept: List[Dict[str, Any]] = []
        seen_signatures: List[Set[str]] = []

        for chunk in chunks:
            words = set(chunk['text'].lower().split())
            if not words:
                continue

            is_dup = False
            for prev_words in seen_signatures:
                intersection = len(words & prev_words)
                union = len(words | prev_words)
                if union > 0 and intersection / union >= self.cfg.dedup_similarity_threshold:
                    is_dup = True
                    logger.debug("Removed near-duplicate chunk: %s...",
                                 chunk['text'][:60])
                    break

            if not is_dup:
                kept.append(chunk)
                seen_signatures.append(words)

        if len(kept) < len(chunks):
            logger.info("Deduplication removed %d chunks", len(chunks) - len(kept))

        return kept

    # ═══════════════════════════════════════════════════════════════════
    #  Small Chunk Merging
    # ═══════════════════════════════════════════════════════════════════

    def _merge_small_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge chunks that are too small to be useful on their own."""
        if len(chunks) <= 1:
            return chunks

        merged: List[Dict[str, Any]] = []
        pending_text = ""
        pending_metadata = None

        for chunk in chunks:
            text = chunk['text']

            if len(text) < self.cfg.min_chunk_length:
                if pending_text:
                    pending_text += "\n\n" + text
                else:
                    pending_text = text
                    pending_metadata = chunk['metadata'].copy()
            else:
                if pending_text:
                    chunk = chunk.copy()
                    chunk['text'] = pending_text + "\n\n" + text
                    pending_text = ""
                    pending_metadata = None
                merged.append(chunk)

        if pending_text:
            if merged:
                merged[-1] = merged[-1].copy()
                merged[-1]['text'] += "\n\n" + pending_text
            else:
                merged.append({
                    'text': pending_text,
                    'metadata': pending_metadata or {}
                })

        return merged

    # ═══════════════════════════════════════════════════════════════════
    #  Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _clean_header(header: str) -> str:
        """Clean and normalize a column header to snake_case."""
        if not header:
            return ""
        header = str(header).strip().lower()
        header = re.sub(r'[./\-]+', '_', header)
        header = re.sub(r'[^a-z0-9_]', '', header)
        header = re.sub(r'_+', '_', header)
        return header.strip('_')

    def get_processing_stats(self) -> Dict[str, Any]:
        """Return summary statistics from the last processing run."""
        return {
            'document_context': self._document_context.copy(),
            'sections_found': list(set(self._procedure_hierarchy.values())),
            'procedures_mapped': len(self._procedure_hierarchy),
            'headers_seen': len(self._seen_headers),
        }


# ── Global instance (backward-compatible) ────────────────────────────
structured_processor = StructuredJSONProcessor()
