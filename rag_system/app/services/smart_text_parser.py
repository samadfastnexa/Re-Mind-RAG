"""
Smart Text Parser
Intelligently extracts structure from narrative text documents.
Converts unstructured procedures into structured metadata.
"""
import re
from typing import Dict, List, Any, Optional, Tuple
import uuid


class SmartTextParser:
    """
    Parse narrative text to extract structured metadata.
    Ideal for procedure manuals, policies, and structured documents in text format.
    """
    
    def __init__(self):
        # Patterns for detecting sections and procedures
        self.section_patterns = [
            r'^(\d+)\.\s+([A-Z][A-Z\s\(\)]+)',  # "16. SERVICE LEVEL AGREEMENT (SLA)"
            r'^(\d+\.\d+)\.\s+([A-Z][A-Z\s\(\)]+)',  # "15.3. PROCESS FLOW"
            r'^(\d+\.\d+\.\d+)\.\s+([A-Z][A-Z\s]+)',  # "9.6.1. PROCEDURE"
            r'^([A-Z][A-Z\s]+:)',  # "PROCEDURE:" or "CONTROL:"
        ]
        
        # Metadata extraction patterns
        self.metadata_patterns = {
            'page': r'(?:page|pg|p\.?)\s*[:\-]?\s*(\d+)',
            'section': r'section\s+(\d+(?:\.\d+)*)',
            'procedure_no': r'procedure\s+(?:no\.?|number|#)\s*[:\-]?\s*([\d\.]+)',
            'control_owner': r'(?:control\s+owner|owner|responsible)[:\-]\s*([A-Za-z\s]+)',
            'priority': r'(?:priority|criticality)[:\-]\s*(critical|high|medium|low)',
            'applies_to': r'applies\s+to[:\-]\s*([A-Za-z\s,]+)',
            'department': r'(?:department|dept)[:\-]\s*([A-Za-z\s]+)',
        }
    
    def parse_document_structure(
        self,
        text: str,
        filename: str,
        document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """
        Parse document text and extract structured chunks.
        
        Args:
            text: Full document text
            filename: Original filename
            document_id: Optional document ID
            
        Returns:
            Tuple of (chunks_with_metadata, document_id, num_sections)
        """
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        
        # Split into sections
        sections = self._split_into_sections(text)
        
        chunks = []
        for idx, section in enumerate(sections):
            # Extract metadata from section
            metadata = self._extract_metadata(section)
            
            # Create chunk
            chunk = {
                "text": section['content'],
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunk_index": idx,
                    "total_chunks": len(sections),
                    "chunk_type": "structured_section",
                    **metadata
                }
            }
            chunks.append(chunk)
        
        return chunks, doc_id, len(sections)
    
    def _split_into_sections(self, text: str) -> List[Dict[str, Any]]:
        """Split text into logical sections based on headings."""
        sections = []
        lines = text.split('\n')
        
        current_section = {
            'title': None,
            'number': None,
            'content': '',
            'start_line': 0
        }
        
        for line_num, line in enumerate(lines):
            # Check if this line is a section heading
            section_match = None
            for pattern in self.section_patterns:
                match = re.match(pattern, line.strip(), re.IGNORECASE)
                if match:
                    section_match = match
                    break
            
            if section_match:
                # Save previous section if it has content
                if current_section['content'].strip():
                    sections.append({
                        'title': current_section['title'],
                        'number': current_section['number'],
                        'content': current_section['content'].strip(),
                        'lines': (current_section['start_line'], line_num - 1)
                    })
                
                # Start new section
                if len(section_match.groups()) >= 2:
                    current_section = {
                        'title': section_match.group(2).strip(),
                        'number': section_match.group(1),
                        'content': line + '\n',
                        'start_line': line_num
                    }
                else:
                    current_section = {
                        'title': section_match.group(1).strip(':').strip(),
                        'number': None,
                        'content': line + '\n',
                        'start_line': line_num
                    }
            else:
                current_section['content'] += line + '\n'
        
        # Add final section
        if current_section['content'].strip():
            sections.append({
                'title': current_section['title'],
                'number': current_section['number'],
                'content': current_section['content'].strip(),
                'lines': (current_section['start_line'], len(lines) - 1)
            })
        
        return sections
    
    def _extract_metadata(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from section content."""
        metadata = {}
        
        # Handle both dict and object access patterns
        try:
            content = section['content'].lower() if isinstance(section, dict) else section.text.lower()
        except (KeyError, AttributeError) as e:
            # If neither works, return empty metadata
            print(f"Warning: Could not extract content from section: {e}")
            return metadata
        
        # Add section info
        if section.get('title'):
            metadata['section_title'] = section['title']
        if section.get('number'):
            metadata['section_id'] = section['number']
            metadata['procedure_no'] = section['number']
        
        # Extract other metadata using patterns
        for key, pattern in self.metadata_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Capitalize values appropriately
                if key in ['control_owner', 'department', 'applies_to']:
                    value = value.title()
                metadata[key] = value
        
        # Infer priority from title/content if not found
        if 'priority' not in metadata:
            if any(word in content for word in ['critical', 'mandatory', 'required']):
                metadata['priority'] = 'High'
            elif any(word in content for word in ['optional', 'recommended']):
                metadata['priority'] = 'Medium'
        
        # Detect compliance frameworks
        compliance_tags = []
        if 'iso 27001' in content or 'iso27001' in content:
            compliance_tags.append('ISO27001')
        if 'gdpr' in content:
            compliance_tags.append('GDPR')
        if 'soc 2' in content or 'soc2' in content:
            compliance_tags.append('SOC2')
        if 'pci' in content:
            compliance_tags.append('PCI-DSS')
        if 'hipaa' in content:
            compliance_tags.append('HIPAA')
        if compliance_tags:
            metadata['compliance_tags'] = compliance_tags
        
        # Categorize by content
        section_title = section.get('title') if isinstance(section, dict) else getattr(section, 'title', None)
        metadata['group'] = self._categorize_section(section_title, content)
        
        return metadata
    
    def _categorize_section(self, title: Optional[str], content: str) -> str:
        """Categorize section based on title and content."""
        if not title:
            title = ""
        
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Category keywords
        categories = {
            'Access Control': ['access', 'authentication', 'authorization', 'login', 'password'],
            'Asset Management': ['asset', 'inventory', 'equipment', 'hardware', 'software'],
            'Backup and Recovery': ['backup', 'recovery', 'restore', 'disaster'],
            'Change Management': ['change', 'deployment', 'release', 'configuration'],
            'Incident Management': ['incident', 'response', 'security event', 'breach'],
            'Network Security': ['network', 'firewall', 'vpn', 'connectivity'],
            'Data Protection': ['data', 'privacy', 'encryption', 'protection'],
            'Compliance': ['compliance', 'audit', 'regulation', 'policy'],
            'Business Continuity': ['continuity', 'availability', 'sla', 'uptime'],
            'User Management': ['user', 'employee', 'onboarding', 'offboarding'],
        }
        
        # Check title and content against categories
        for category, keywords in categories.items():
            if any(keyword in title_lower or keyword in content_lower for keyword in keywords):
                return category
        
        return 'General'
    
    def enhance_chunks_with_structure(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enhance existing chunks with extracted structure.
        Use this to add metadata to chunks from other processors.
        """
        enhanced_chunks = []
        
        for chunk in chunks:
            # Support both 'text' (standard) and 'content' (legacy) keys
            text = chunk.get('text', '') or chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            
            # Extract additional metadata
            extracted_metadata = self._extract_metadata({
                'title': None,
                'number': None,
                'content': text,
                'lines': (0, 0)
            })
            
            # Merge metadata (don't overwrite existing)
            for key, value in extracted_metadata.items():
                if key not in metadata:
                    metadata[key] = value
            
            enhanced_chunks.append({
                'text': text,
                'metadata': metadata
            })
        
        return enhanced_chunks


# Global instance
smart_text_parser = SmartTextParser()
