"""HTML parser for Blender Python API documentation."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocEntry:
    """Represents a documented function/class/property in Blender API."""
    
    function_path: str      # e.g., "bpy.ops.mesh.subdivide" or "bpy.types.Mesh"
    title: str             # Human readable title
    description: str       # Short description
    signature: Optional[str] = None     # Function signature if available
    parameters: List[Dict[str, Any]] = None  # Parameter info
    return_type: Optional[str] = None   # Return type if specified
    example_code: Optional[str] = None  # Code example if available
    module: str = ""       # Module name (e.g., "bpy.ops.mesh")
    doc_type: str = ""     # "function", "class", "property"
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        
        # Extract module from function path
        if not self.module and self.function_path:
            parts = self.function_path.split('.')
            if len(parts) > 1:
                self.module = '.'.join(parts[:-1])


class BlenderDocParser:
    """Parser for Blender Python API HTML documentation."""
    
    def __init__(self):
        self.entries: List[DocEntry] = []
    
    def parse_file(self, html_path: Path) -> List[DocEntry]:
        """Parse a single HTML file and extract documentation entries."""
        
        logger.info(f"Parsing {html_path.name}")
        entries = []
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Extract module name from title or content
            module_name = self._extract_module_name(soup)
            
            # Parse functions (bpy.ops.* style)
            entries.extend(self._parse_functions(soup, module_name))
            
            # Parse classes (bpy.types.* style)
            entries.extend(self._parse_classes(soup, module_name))
            
        except Exception as e:
            logger.error(f"Error parsing {html_path}: {e}")
        
        return entries
    
    def _extract_module_name(self, soup: BeautifulSoup) -> str:
        """Extract the module name from the page."""
        
        # Try to get from module header
        module_header = soup.find('section', id=lambda x: x and x.startswith('module-'))
        if module_header:
            module_id = module_header.get('id', '')
            return module_id.replace('module-', '')
        
        # Try to get from title
        title = soup.find('title')
        if title:
            # Extract module from title like "Mesh Operators — Blender Python API"
            title_text = title.text
            if 'bpy.' in title_text:
                match = re.search(r'(bpy\.[.\w]+)', title_text)
                if match:
                    return match.group(1)
        
        return ""
    
    def _parse_functions(self, soup: BeautifulSoup, module_name: str) -> List[DocEntry]:
        """Parse function definitions from the HTML."""
        
        entries = []
        
        # Find all function definitions
        for func_dt in soup.find_all('dt', class_='sig sig-object py'):
            if not func_dt.get('id'):
                continue
            
            try:
                entry = self._extract_function_info(func_dt, module_name)
                if entry:
                    entries.append(entry)
            except Exception as e:
                logger.warning(f"Error parsing function: {e}")
        
        return entries
    
    def _extract_function_info(self, func_dt: Tag, module_name: str) -> Optional[DocEntry]:
        """Extract information from a function definition."""
        
        # Get function ID (full path)
        func_id = func_dt.get('id', '')
        if not func_id:
            return None
        
        # Get function signature
        signature_parts = []
        for elem in func_dt.find_all(['span'], class_=['sig-prename', 'sig-name', 'sig-paren']):
            signature_parts.append(elem.get_text(strip=True))
        
        # Get parameter list
        params_text = ""
        sig_params = func_dt.find_all('em', class_='sig-param')
        if sig_params:
            params_text = ", ".join([p.get_text(strip=True) for p in sig_params])
        
        full_signature = ''.join(signature_parts)
        if params_text:
            # Insert parameters into signature
            full_signature = full_signature.replace('()', f"({params_text})")
        
        # Get description from the following dd tag
        desc_dd = func_dt.find_next_sibling('dd')
        description = ""
        parameters = []
        
        if desc_dd:
            # Get main description
            desc_p = desc_dd.find('p')
            if desc_p:
                description = desc_p.get_text(strip=True)
            
            # Extract parameters
            params_section = desc_dd.find('dl', class_='field-list')
            if params_section:
                parameters = self._extract_parameters(params_section)
        
        # Determine if it's a function or class
        doc_type = "function"
        if 'bpy.types.' in func_id and func_id.count('.') == 2:
            doc_type = "class"
        
        return DocEntry(
            function_path=func_id,
            title=func_id.split('.')[-1],
            description=description,
            signature=full_signature,
            parameters=parameters,
            module=module_name or func_id.rsplit('.', 1)[0],
            doc_type=doc_type
        )
    
    def _parse_classes(self, soup: BeautifulSoup, module_name: str) -> List[DocEntry]:
        """Parse class definitions and their properties."""
        
        entries = []
        
        # Find class definitions
        for class_elem in soup.find_all('dl', class_='py class'):
            class_dt = class_elem.find('dt')
            if not class_dt or not class_dt.get('id'):
                continue
            
            class_id = class_dt.get('id', '')
            
            # Get class description
            class_desc = ""
            desc_dd = class_dt.find_next_sibling('dd')
            if desc_dd:
                desc_p = desc_dd.find('p')
                if desc_p:
                    class_desc = desc_p.get_text(strip=True)
            
            # Add class entry
            entries.append(DocEntry(
                function_path=class_id,
                title=class_id.split('.')[-1],
                description=class_desc,
                module=module_name or class_id.rsplit('.', 1)[0],
                doc_type="class"
            ))
            
            # Parse class properties/methods
            if desc_dd:
                for prop_dl in desc_dd.find_all('dl', class_='py data'):
                    prop_entry = self._extract_property_info(prop_dl, class_id)
                    if prop_entry:
                        entries.append(prop_entry)
        
        return entries
    
    def _extract_property_info(self, prop_dl: Tag, parent_class: str) -> Optional[DocEntry]:
        """Extract property information from a class."""
        
        prop_dt = prop_dl.find('dt')
        if not prop_dt or not prop_dt.get('id'):
            return None
        
        prop_id = prop_dt.get('id', '')
        prop_name = prop_id.split('.')[-1]
        
        # Get description
        desc_dd = prop_dt.find_next_sibling('dd')
        description = ""
        prop_type = ""
        
        if desc_dd:
            desc_p = desc_dd.find('p')
            if desc_p:
                description = desc_p.get_text(strip=True)
            
            # Get type info
            type_info = desc_dd.find('dl', class_='field-list')
            if type_info:
                type_field = type_info.find('dt', string='Type')
                if type_field:
                    type_dd = type_field.find_next_sibling('dd')
                    if type_dd:
                        prop_type = type_dd.get_text(strip=True)
        
        return DocEntry(
            function_path=prop_id,
            title=prop_name,
            description=f"{description} (Type: {prop_type})" if prop_type else description,
            module=parent_class,
            doc_type="property"
        )
    
    def _extract_parameters(self, params_dl: Tag) -> List[Dict[str, Any]]:
        """Extract parameter information from a field list."""
        
        parameters = []
        
        params_dt = params_dl.find('dt', string=re.compile('Parameters?'))
        if params_dt:
            params_dd = params_dt.find_next_sibling('dd')
            if params_dd:
                param_list = params_dd.find('ul')
                if param_list:
                    for param_li in param_list.find_all('li', recursive=False):
                        param_info = self._parse_parameter_item(param_li)
                        if param_info:
                            parameters.append(param_info)
        
        return parameters
    
    def _parse_parameter_item(self, param_li: Tag) -> Optional[Dict[str, Any]]:
        """Parse a single parameter list item."""
        
        text = param_li.get_text(strip=True)
        
        # Try to extract parameter name and description
        # Format: "name (type, optional) – Description"
        match = re.match(r'^(\w+)\s*\(([^)]+)\)\s*–\s*(.+)$', text)
        if match:
            return {
                'name': match.group(1),
                'type': match.group(2),
                'description': match.group(3)
            }
        
        # Simpler format without parentheses
        match = re.match(r'^(\w+)\s*–\s*(.+)$', text)
        if match:
            return {
                'name': match.group(1),
                'type': 'unknown',
                'description': match.group(2)
            }
        
        return None


def parse_all_docs(docs_dir: Path) -> List[DocEntry]:
    """Parse all HTML files in the documentation directory."""
    
    parser = BlenderDocParser()
    all_entries = []
    
    # Get all HTML files
    html_files = list(docs_dir.glob('*.html'))
    logger.info(f"Found {len(html_files)} HTML files to parse")
    
    # Parse each file
    for html_file in html_files:
        entries = parser.parse_file(html_file)
        all_entries.extend(entries)
    
    logger.info(f"Parsed {len(all_entries)} documentation entries")
    return all_entries


if __name__ == "__main__":
    # Test parsing
    docs_dir = Path(__file__).parent.parent / "blender_python_reference_4_5"
    
    if docs_dir.exists():
        entries = parse_all_docs(docs_dir)
        
        # Print some examples
        print(f"\nTotal entries parsed: {len(entries)}")
        print("\nExample entries:")
        
        for i, entry in enumerate(entries[:5]):
            print(f"\n{i+1}. {entry.function_path}")
            print(f"   Type: {entry.doc_type}")
            print(f"   Description: {entry.description[:100]}...")
            if entry.signature:
                print(f"   Signature: {entry.signature[:100]}...")