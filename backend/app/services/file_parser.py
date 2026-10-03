import io
from typing import Tuple, Optional
from pypdf import PdfReader
import docx
from app.schemas import ProcessingError

class FileParserService:
    @staticmethod
    def parse_file_content(filename: str, file_bytes: bytes) -> Tuple[Optional[str], Optional[ProcessingError]]:
        if not file_bytes or len(file_bytes) == 0:
            return None, ProcessingError(
                filename=filename,
                error_code="EMPTY_FILE",
                user_message="The uploaded file contains 0 bytes.",
                action_suggested="Please check the file and upload a non-empty document."
            )
            
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        try:
            if ext == 'txt':
                text = file_bytes.decode('utf-8', errors='ignore')
                if not text.strip():
                    return None, ProcessingError(
                        filename=filename,
                        error_code="EMPTY_TEXT",
                        user_message="No readable text content found in text file.",
                        action_suggested="Upload a valid text file with content."
                    )
                return text, None
                
            elif ext == 'pdf':
                pdf_file = io.BytesIO(file_bytes)
                reader = PdfReader(pdf_file)
                if len(reader.pages) == 0:
                    return None, ProcessingError(
                        filename=filename,
                        error_code="CORRUPTED_PDF",
                        user_message="PDF contains 0 pages or has invalid structure.",
                        action_suggested="Ensure the file is a valid PDF."
                    )
                
                text_content = []
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                        
                extracted = "\n".join(text_content).strip()
                if not extracted:
                    return None, ProcessingError(
                        filename=filename,
                        error_code="SCANNED_PDF_NO_TEXT",
                        user_message="PDF appears to be a scanned image or lacks selectable text.",
                        action_suggested="Convert scanned PDF using OCR or upload plain text format."
                    )
                return extracted, None
                
            elif ext == 'docx':
                docx_file = io.BytesIO(file_bytes)
                doc = docx.Document(docx_file)
                text_content = [p.text for p in doc.paragraphs if p.text.strip()]
                extracted = "\n".join(text_content).strip()
                if not extracted:
                    return None, ProcessingError(
                        filename=filename,
                        error_code="EMPTY_DOCX",
                        user_message="DOCX document contains no paragraph text.",
                        action_suggested="Check document contents."
                    )
                return extracted, None
                
            else:
                return None, ProcessingError(
                    filename=filename,
                    error_code="UNSUPPORTED_FORMAT",
                    user_message=f"Unsupported file format '.{ext}'. Supported formats: .pdf, .docx, .txt",
                    action_suggested="Upload resumes in PDF, DOCX, or TXT formats."
                )
                
        except Exception as e:
            return None, ProcessingError(
                filename=filename,
                error_code="CORRUPTED_FILE",
                user_message=f"Could not parse file structure: {str(e)}",
                action_suggested="File may be encrypted or corrupted. Try re-saving the file."
            )
