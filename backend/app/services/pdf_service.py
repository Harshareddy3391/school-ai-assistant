import fitz

def extract_text_from_pdf(file_path:str)-> list[dict]:

    """
    Extract text from  a PDF page by page.
    
    """

    pages=[]

    try:
        pdf_document=fitz.open(file_path)

        for page_number,page in enumerate(pdf_document,start=1):
            text=page.get_text("text").strip()

            if text :
                pages.append({"page_number":page_number,"text":text})


        pdf_document.close()

        return pages


    except Exception as e:
        raise RuntimeError(
            f"Failed to extract text from PDF:{str(e)}"
        )
    
