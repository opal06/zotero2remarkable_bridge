import fitz
import json
from pathlib import Path

def save_pdf(pdf):
    if pdf.can_save_incrementally():
        pdf.save(temp_path / pdf_name, incremental=True, encryption=0)
        pdf.close()
        pdf_name = pdf
    else:
        pdf_hl = (temp_path / pdf_name).with_suffix(".pdf.hl")
        pdf.save(pdf_hl)
        pdf.close()
        (temp_path / pdf_name).unlink()
        pdf_name = pdf_hl.with_suffix(".pdf")
    return pdf_name


def get_scale(page_rect):
    """ This part was inspired by rmrl's implementation"""
    display = {
        "screenwidth": 1404,
        "screenheight": 1872,
        "realwidth": 1408,
        "dpi": 226
    }    
    ptperpx = display["dpi"] / 72
    pdf_height = display["screenheight"] * ptperpx
    #pdf_width = display["screenwidth"] * ptperpx
    scale = round(page_rect.y1) / pdf_height
    return scale


def add_highlights_simple(entity, content_id, pdf_name):
    temp_path = Path(tempfile.gettempdir())
    work_dir = temp_path / "unzipped"
    highlights_dir = work_dir / (content_id + ".highlights")
    
    # Highlighter colors are saved as integers by ReMarkable: 0 = yellow, 4 = green, 5 = pink
    colors = {0 : [1.0, 1.0, 0.0], 4 : [0.0, 1.0, 0.3], 5 : [1.0, 0.0, 0.7]}
    
    if highlights_dir.is_dir():
         
        pdf = fitz.open(temp_path / pdf_name)            
        
        for highlights_file in highlights_dir.iterdir():
            highlights_id = highlights_file.stem
                    
            with open(highlights_file, "r", encoding="utf-8") as hl:
                hl_json = json.load(hl)
            hl_list = hl_json["highlights"][0]
                            
            with open(work_dir / (content_id + ".content"), "r") as content_file:
                content_json = json.load(content_file)
            page_nr = content_json["pages"].index(highlights_id)
                                                 
            page = pdf.load_page(page_nr)
                
            for hl in hl_list:
                if "\u0002" in hl["text"]:
                    search_text = hl["text"].replace("\u0002", "")
                else:
                    search_text = hl["text"]
                quads = page.search_for(search_text, quads=True)                  
                    
                if quads != []:                    
                    highlight = page.add_highlight_annot(quads)
                else:
                    print("Failed to create highlight on " + str(page_nr + 1) + "...")
                
                if "color" in hl:
                    highlight_color = colors[hl["color"]]
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
            
        print("Added annotations to file")
        
        pdf_name = save_pdf(pdf)
        
        print("Saved PDF as " + str(pdf_name))
        #rmtree(work_dir)
        
    else:
        print("No highlights found, skipping...")                     
            
                
