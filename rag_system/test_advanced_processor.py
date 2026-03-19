"""
Comprehensive test for the Advanced Structured Processor.

Tests all features: backward compatibility, config, statistical typing,
quality scoring, dedup, cross-page continuity, hierarchical grouping.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.structured_processor import StructuredJSONProcessor, ProcessorConfig

PASS = 0
FAIL = 0

def check(test_name, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  ✓ {test_name}")
    else:
        FAIL += 1
        print(f"  ✗ {test_name}")
        print(f"    Expected: {expected}")
        print(f"    Actual:   {actual}")

def check_in(test_name, needle, haystack):
    global PASS, FAIL
    if needle in haystack:
        PASS += 1
        print(f"  ✓ {test_name}")
    else:
        FAIL += 1
        print(f"  ✗ {test_name}")
        print(f"    '{needle}' not found in output")


# ══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("TEST 1: ProcessorConfig defaults + custom config")
print("=" * 70)

cfg = ProcessorConfig()
check("Default min_chunk_length", cfg.min_chunk_length, 80)
check("Default merge_column_threshold", cfg.merge_column_threshold, 8)
check("Default dedup_similarity_threshold", cfg.dedup_similarity_threshold, 0.90)

custom = ProcessorConfig(min_chunk_length=50, merge_column_threshold=6)
proc_custom = StructuredJSONProcessor(config=custom)
check("Custom min_chunk_length", proc_custom.cfg.min_chunk_length, 50)
check("Custom merge_threshold", proc_custom.cfg.merge_column_threshold, 6)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 2: _merge_misaligned_columns")
print("=" * 70)

proc = StructuredJSONProcessor()

table_12col = [
    [None, "No.", None, "Procedures", None, "Control", None, "Control Owner", None, "Channel", None, "Document"],
    ["6.3.1", None, "The Annual IT Plan shall be prepared", None, "Ensure the IT Plan is prepared.", None, "Respective C Officers", None, "Email", None, "ITD-P1-P05", None],
    ["6.3.2", None, "By 5th May of every year", None, "Ensure the Annual IT Plan is approved.", None, "CSO", None, "Email", None, "N/A", None],
]

cleaned = proc._remove_empty_columns(table_12col)
merged = proc._merge_misaligned_columns(cleaned)
check("Merge reduces to 6 columns", len(merged[0]), 6)
check("Data[0] = 6.3.1", merged[1][0], "6.3.1")
check("Data[5] = ITD-P1-P05", merged[1][5], "ITD-P1-P05")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 3: _is_header_continuation")
print("=" * 70)

row1 = ["No.", "Procedures", "Control", "Control", "Channel", "Document"]
row2 = ["", "", "", "Owner", "", ""]
check("Control + Owner → continuation", proc._is_header_continuation(row1, row2), True)

row2_data = ["6.3.1", "Plan shall be prepared", "Ensure plan", "Officers", "Email", "ITD"]
check("Data row ≠ continuation", proc._is_header_continuation(row1, row2_data), False)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 4: _infer_headers_from_data")
print("=" * 70)

table_no_header = [
    ["7.1.1", "All network devices must be secured in lockable racks for safety.", "Devices must be in lockable racks.", "CTO", "N/A", "N/A"],
    ["7.1.2", "Physical access to server rooms restricted to authorised personnel only.", "Restricted access to server rooms.", "CTO", "N/A", "N/A"],
]

headers_inf = proc._infer_headers_from_data(table_no_header)
check("Col 0 = no", headers_inf[0], "no")
check("Col 1 = procedures", headers_inf[1], "procedures")
check("Col 3 = control_owner", headers_inf[3], "control_owner")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 5: _infer_field_label")
print("=" * 70)

check("7.1.1 → Procedure No.", proc._infer_field_label("field_1", "7.1.1"), "Step/Procedure No.")
check("Ensure → Control Objective", proc._infer_field_label("field_3", "Ensure final approval."), "Control Objective")
check("CTO → Control Owner", proc._infer_field_label("field_4", "CTO"), "Control Owner")
check("Email → Channel", proc._infer_field_label("field_5", "Email"), "Communication Channel")
check("N/A → generic", "Communication Channel" != proc._infer_field_label("field_6", "N/A"), True)
check("ITD-P1-P05 → Reference", proc._infer_field_label("field_6", "ITD-P1-P05"), "Reference Document")
long_text = "The Annual IT Plan shall be prepared by IT department. " * 3
check("Long text → Procedure", proc._infer_field_label("field_2", long_text), "Procedure")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 6: Statistical column type refinement")
print("=" * 70)

proc2 = StructuredJSONProcessor()
# Simulate: headers are generic, but data rows clearly match patterns
generic_headers = ['field_1', 'field_2', 'field_3', 'field_4', 'field_5', 'field_6']
data_rows = [
    ["6.3.1", "The Annual IT Plan shall be prepared by the department for review and approval by the committee.", "Ensure the IT Plan is prepared.", "CTO", "Email", "ITD-P1-P05"],
    ["6.3.2", "By 5th May of every year the plan shall be submitted to the steering committee for approval.", "Ensure the Annual IT Plan is approved.", "CSO", "Email", "N/A"],
    ["6.3.3", "By 10th May the approved plan shall be distributed to all departments for implementation.", "Ensure final approval by CEO.", "Director Strategy", "Meeting", "N/A"],
]

refined = proc2._refine_headers_statistically(generic_headers, data_rows)
print(f"  Refined: {refined}")
check("Stat: col 0 → no", refined[0], "no")
check("Stat: col 1 → procedures", refined[1], "procedures")
check("Stat: col 2 → control", refined[2], "control")
check("Stat: col 3 → control_owner", refined[3], "control_owner")
check("Stat: col 4 → channel", refined[4], "channel")
check("Stat: col 5 → document", refined[5], "document")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 7: Chunk quality scoring")
print("=" * 70)

proc3 = StructuredJSONProcessor()

# Good chunk: lots of fields, good length, has context
good_item = {
    'no': '6.3.1',
    'procedures': 'The Annual IT Plan shall be prepared.',
    'control': 'Ensure the IT Plan is prepared.',
    'control_owner': 'CTO',
    'channel': 'Email',
    'document': 'ITD-P1-P05',
    '_document_context': {'document_no': 'FCL|SOP|ITD|01'},
    '_section': 'IT Planning',
    '_source_page': 1,
    '_table_index': 0,
    '_row_index': 0,
}
good_chunk = proc3._create_structured_chunk(good_item, 'doc1', 'test.pdf', 0)
good_score = proc3._score_chunk_quality(good_chunk)
print(f"  Good chunk score: {good_score}")
check("Good chunk score > 0.7", good_score > 0.7, True)

# Bad chunk: only 1 field, short, no context
bad_item = {
    'field_1': 'N/A',
    '_source_page': 1,
    '_table_index': 0,
    '_row_index': 0,
}
bad_chunk = proc3._create_structured_chunk(bad_item, 'doc1', 'test.pdf', 1)
bad_score = proc3._score_chunk_quality(bad_chunk)
print(f"  Bad chunk score: {bad_score}")
check("Bad chunk score < 0.5", bad_score < 0.5, True)
check("Good > Bad", good_score > bad_score, True)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 8: Near-duplicate removal")
print("=" * 70)

proc4 = StructuredJSONProcessor()

chunks = [
    {'text': 'Step 6.3.1: The Annual IT Plan shall be prepared by the department.', 'metadata': {'chunk_index': 0}},
    {'text': 'Step 6.3.1: The Annual IT Plan shall be prepared by the department.', 'metadata': {'chunk_index': 1}},  # exact dup
    {'text': 'Step 6.3.2: By 5th May the plan shall be submitted.', 'metadata': {'chunk_index': 2}},
]

deduped = proc4._deduplicate_chunks(chunks)
check("Dedup removes exact duplicate", len(deduped), 2)
check("Dedup keeps first occurrence", deduped[0]['metadata']['chunk_index'], 0)
check("Dedup keeps different chunk", deduped[1]['metadata']['chunk_index'], 2)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 9: Cross-page table continuity")
print("=" * 70)

proc5 = StructuredJSONProcessor()
proc5._prev_page_table_headers = ['no', 'procedures', 'control', 'control_owner', 'channel', 'document']

# Table on page 2 with repeated header row then data
table_p2 = [
    ["No.", "Procedures", "Control", "Control Owner", "Channel", "Document"],  # repeated header
    ["7.1.1", "All devices must be secured.", "Devices in lockable racks.", "CTO", "N/A", "N/A"],
]

result = proc5._handle_cross_page_continuity(table_p2, page_num=2)
check("Cross-page strips header", len(result), 1)
check("Cross-page keeps data", result[0][0], "7.1.1")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 10: Full pipeline (simulated)")
print("=" * 70)

proc6 = StructuredJSONProcessor()
merged_table = [
    ["No.", "Procedures", "Control", "Control Owner", "Channel", "Document"],
    ["6.3.1", "The Annual IT Plan shall be prepared", "Ensure the IT Plan is prepared.", "Respective C Officers", "Email", "ITD-P1-P05"],
    ["6.3.2", "By 5th May of every year", "Ensure the Annual IT Plan is approved.", "CSO", "Email", "N/A"],
]

headers, hrows = proc6._extract_smart_headers(merged_table)
check("Header: no", headers[0], "no")
check("Header: procedures", headers[1], "procedures")
check("Header: control_owner", headers[3], "control_owner")

item = proc6._row_to_item(merged_table[1], headers)
item['_document_context'] = {'document_no': 'FCL|SOP|ITD|01', 'version': '1.00'}
text = proc6._json_to_searchable_text(item)

check_in("Text has procedure no", "Step/Procedure No.: 6.3.1", text)
check_in("Text has control objective", "Control Objective:", text)
check_in("Text has Reference Document", "Reference Document: ITD-P1-P05", text)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 11: Hierarchical grouping")
print("=" * 70)

proc7 = StructuredJSONProcessor()
proc7._current_section = "Software and Network Security"
proc7._procedure_hierarchy['7.1.1'] = "Software and Network Security"

item_h = {
    'no': '7.1.1',
    'procedures': 'All devices must be secured.',
    '_document_context': {'document_no': 'FCL|SOP|ITD|01'},
    '_section': 'Software and Network Security',
    '_source_page': 3,
    '_table_index': 0,
    '_row_index': 0,
}
chunk_h = proc7._create_structured_chunk(item_h, 'doc1', 'test.pdf', 0)
check("Hierarchy: parent_section", chunk_h['metadata'].get('parent_section'), "Software and Network Security")
check("Hierarchy: section", chunk_h['metadata'].get('section'), "Software and Network Security")


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 12: get_processing_stats()")
print("=" * 70)

proc8 = StructuredJSONProcessor()
proc8._document_context = {'document_no': 'FCL|SOP|ITD|01', 'version': '1.00'}
proc8._procedure_hierarchy = {'6.3.1': 'IT Planning', '6.3.2': 'IT Planning', '7.1.1': 'Network Security'}

stats = proc8.get_processing_stats()
check("Stats: document_context present", 'document_no' in stats['document_context'], True)
check("Stats: sections found", len(stats['sections_found']), 2)
check("Stats: procedures mapped", stats['procedures_mapped'], 3)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 13: _score_column_type helper")
print("=" * 70)

from app.services.structured_processor import _COL_PATTERNS

no_values = ["6.3.1", "6.3.2", "6.3.3", "7.1.1"]
no_score = StructuredJSONProcessor._score_column_type(no_values, 'no', _COL_PATTERNS['no'])
check("Column type score for 'no' = 1.0", no_score, 1.0)

mixed_values = ["6.3.1", "some text", "7.1.1", "more text"]
mixed_score = StructuredJSONProcessor._score_column_type(mixed_values, 'no', _COL_PATTERNS['no'])
check("Column type score mixed = 0.5", mixed_score, 0.5)

channel_values = ["Email", "Phone", "Meeting", "Email"]
ch_score = StructuredJSONProcessor._score_column_type(channel_values, 'channel', _COL_PATTERNS['channel'])
check("Column type score channel = 1.0", ch_score, 1.0)


# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 70)

if FAIL > 0:
    print("\n⚠ SOME TESTS FAILED")
    sys.exit(1)
else:
    print("\n✓ ALL TESTS PASSED")
    sys.exit(0)
