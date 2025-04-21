from shiny import App, ui, render, reactive, req
import tempfile
import os
import difflib
from pathlib import Path
import PyPDF2
import shutil  # For cleaning up temp directory
import base64 


# Define the UI
app_ui = ui.page_sidebar(   
    # Sidebar with the report selector
    ui.sidebar(
        ui.h3("Report Selection"),
        ui.input_select(
            "report_type",
            "Select Report Type:",
            {
                "financial": "Financial Statements",
                "aum": "AUM (Assets Under Management)",
                "daily": "Daily Checks",
                "monthly": "Monthly Checks",
                "pdf_compare": "PDF Comparison Tool"  
            }
        ),
        ui.hr(),
        ui.p("Select a report type from the dropdown to view its content."),
        fluid=True
    ),
    
    # Main content area with cards for each report type
    ui.output_ui("report_content")

)

# Define the server logic
def server(input, output, session):
    # Current page tracker
    current_page = reactive.value(1)

    # Add handlers for the page navigation buttons:
    @reactive.effect
    @reactive.event(input.next_page)
    def _():
        if not pdf_results.get()["has_compared"]:
            return
        
        max_pages = pdf_results.get()["summary"]["max_pages"]
        new_page = min(current_page.get() + 1, max_pages)
        current_page.set(new_page)
        # Update the goto page input
        ui.update_numeric("goto_page", value=new_page)

    @reactive.effect
    @reactive.event(input.prev_page)
    def _():
        # Add a debugging notification
        # ui.notification_show(f"Previous button clicked, current page: {current_page.get()}")
        
        if not pdf_results.get()["has_compared"]:
            return
        
        new_page = max(current_page.get() - 1, 1)
        current_page.set(new_page)
        # Update the goto page input
        ui.update_numeric("goto_page", value=new_page)
        
        # Add another notification to confirm the page was updated
        # ui.notification_show(f"Page updated to: {current_page.get()}")

    @reactive.effect
    @reactive.event(input.goto_page)
    def _():
        if not pdf_results.get()["has_compared"]:
            return
        
        max_pages = pdf_results.get()["summary"]["max_pages"]
        new_page = max(1, min(input.goto_page(), max_pages))
        current_page.set(new_page)

    # Add an output to display the current page and total pages
    @output
    @render.text
    def current_page_display():
        if not pdf_results.get()["has_compared"]:
            return "Please compare documents first to view pages"
        
        max_pages = pdf_results.get()["summary"]["max_pages"]
        return f"Page {current_page.get()} of {max_pages}"


    # Create a directory for our temporary files that will persist during the session
    temp_dir = tempfile.mkdtemp()

    # Add cleanup when session ends
    @reactive.effect
    def _():
        session.on_ended(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
    
    # Add cleanup when session ends
    @reactive.effect
    def _():
        session.on_ended(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
    
    # Store the results of PDF processing
    pdf_results = reactive.value({
        "text_diff": None,
        "summary": None,
        "has_compared": False,
        "original_pdf_path": None,  
        "comparison_pdf_path": None,  
        "original_text": None,
        "comparison_text": None,
        "summary": {
            "added_lines": 0,
            "removed_lines": 0,
            "total_changes": 0,
            "original_name": "",  
            "comparison_name": ""  
        }
    })
    
    @output
    @render.text
    def report_title():
        # Get the selected report title
        report_types = {
            "financial": "Financial Statements",
            "aum": "AUM (Assets Under Management)",
            "daily": "Daily Checks",
            "monthly": "Monthly Checks",
            "pdf_compare": "PDF Comparison Tool"  # Added new title
        }
        return report_types[input.report_type()]
    
    @output
    @render.ui
    def report_content():
        # Display different content based on the selected report
        if input.report_type() == "financial":
            return ui.card(
                ui.h4("Financial Statement Reports"),
                ui.p("This section contains financial statement reports including:"),
                ui.tags.ul(
                    ui.tags.li("Balance Sheet"),
                    ui.tags.li("Income Statement"),
                    ui.tags.li("Cash Flow Statement"),
                    ui.tags.li("Statement of Changes in Equity")
                ),
                ui.p("Select the specific report you want to view below:"),
                ui.input_select(
                    "financial_report",
                    "Select Financial Report:",
                    {"bs": "Balance Sheet", "is": "Income Statement", 
                     "cf": "Cash Flow", "sce": "Changes in Equity"}
                ),
                ui.br(),
                ui.p("Sample data would be loaded here based on your selection.")
            )
            
        elif input.report_type() == "aum":
            return ui.card(
                ui.h4("Assets Under Management Reports"),
                ui.p("Monitor your AUM with these reports:"),
                ui.tags.ul(
                    ui.tags.li("AUM by Client"),
                    ui.tags.li("AUM by Asset Class"),
                    ui.tags.li("AUM Growth Trend"),
                    ui.tags.li("AUM Regional Breakdown")
                ),
                ui.input_date_range("aum_date_range", "Select Date Range:"),
                ui.br(),
                ui.p("AUM visualization would appear here based on selected dates.")
            )
            
        elif input.report_type() == "daily":
            return ui.card(
                ui.h4("Daily Checks"),
                ui.p("Daily operational checks include:"),
                ui.tags.ul(
                    ui.tags.li("Trade Reconciliation"),
                    ui.tags.li("Cash Balance Verification"),
                    ui.tags.li("NAV Calculation Review"),
                    ui.tags.li("Daily P&L Review")
                ),
                ui.input_date("daily_date", "Select Date:", value="2023-05-01"),
                ui.br(),
                ui.p("Daily check results would be displayed here for the selected date.")
            )
            
        elif input.report_type() == "monthly":
            return ui.card(
                ui.h4("Monthly Checks"),
                ui.p("Monthly compliance and performance checks:"),
                ui.tags.ul(
                    ui.tags.li("Performance Attribution"),
                    ui.tags.li("Compliance Verification"),
                    ui.tags.li("Expense Ratio Analysis"),
                    ui.tags.li("Client Reporting Package")
                ),
                ui.input_select(
                    "month_select",
                    "Select Month:",
                    {"01": "January", "02": "February", "03": "March", 
                     "04": "April", "05": "May", "06": "June",
                     "07": "July", "08": "August", "09": "September",
                     "10": "October", "11": "November", "12": "December"}
                ),
                ui.input_numeric("year_select", "Select Year:", value=2023),
                ui.br(),
                ui.p("Monthly check data would be loaded here for the selected period.")
            )
            
        # PDF Comparison Tool section
        elif input.report_type() == "pdf_compare":
            return ui.card(
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Original Document"),
                        ui.input_file("pdf_original", "", accept=[".pdf"]),
                        ui.output_text("original_pdf_info"),
                    ),
                    ui.card(
                        ui.card_header("Comparison Document"),
                        ui.input_file("pdf_comparison", "", accept=[".pdf"]),
                        ui.output_text("comparison_pdf_info"),
                    ),
                    ui.card(
                        ui.card_header("Run Comparision"),
                        ui.input_action_button("compare_pdfs", "Compare Documents", class_="btn-primary")
                    )
                ),
                
                # Use output_ui to conditionally show the PDF viewers and navigation
                ui.output_ui("pdf_comparison_results")
            )
    
    # onditionally show the PDF viewers and navigation
    @output
    @render.ui
    def pdf_comparison_results():
        if not pdf_results.get()["has_compared"]:
            return None  # Return nothing if comparison hasn't been run
        
        return ui.div(
            ui.card(
                ui.layout_columns(
                    ui.column(6, 
                        ui.h5("Original PDF"),
                        ui.output_ui("original_pdf_viewer")
                    ),
                    ui.column(6, 
                        ui.h5("Comparison PDF"),
                        ui.output_ui("comparison_pdf_viewer")
                    ),
                    gap="10px"
                ),
                ui.output_text("current_page_display"),
                ui.layout_columns(
                    ui.column(4, ui.input_action_button("prev_page", "← Previous Page", width="100%")),
                    ui.column(4, ui.input_numeric("goto_page", "Go to page:", 1, min=1, width="100%")),
                    ui.column(4, ui.input_action_button("next_page", "Next Page →", width="100%"))
                ),
                style="text-align: center; margin: 15px 0;"
            ),
            ui.output_ui("page_differences")
    )
    
    
    # Display information about the original PDF
    @output
    @render.text
    def original_pdf_info():
        if not input.pdf_original():
            return "No file uploaded yet."
        file_info = input.pdf_original()[0]
        return f"File name: {file_info['name']}\nSize: {file_info['size'] / 1024:.2f} KB"
    
    # Display information about the comparison PDF
    @output
    @render.text
    def comparison_pdf_info():
        if not input.pdf_comparison():
            return "No file uploaded yet."
        file_info = input.pdf_comparison()[0]
        return f"File name: {file_info['name']}\nSize: {file_info['size'] / 1024:.2f} KB"
  
    def extract_text_from_pdf(file_info):
        """Extract text from PDF and return both complete text and per-page text"""
        # Create a permanent file in our temp directory
        file_name = f"{os.path.splitext(file_info['name'])[0]}_{os.path.basename(file_info['datapath'])}.pdf"
        temp_path = os.path.join(temp_dir, file_name)
        
        # Copy the uploaded file to our temp directory
        with open(file_info['datapath'], 'rb') as src_file:
            file_content = src_file.read()
            with open(temp_path, 'wb') as dest_file:
                dest_file.write(file_content)
        
        # Extract text using PyPDF2
        try:
            text_content = []
            text_by_page = {}
            
            with open(temp_path, 'rb') as file:
                # Create a PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Get the number of pages
                num_pages = len(pdf_reader.pages)
                
                # Extract text from each page
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:  # Only add non-empty text
                        text_content.append(text)
                        text_by_page[page_num + 1] = text  # Store by page number (1-based)
            
            # Join all pages with newlines and return
            return "\n".join(text_content), temp_path, text_by_page
        
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    #  PDF viewers to use the current_page reactive value
    @output
    @render.ui
    def original_pdf_viewer():
        if not pdf_results.get()["has_compared"]:
            return ui.p("Please compare documents first to view PDFs")
        
        orig_path = pdf_results.get()["original_pdf_path"]
        page = current_page.get() 
        
        if orig_path and os.path.exists(orig_path):
            with open(orig_path, "rb") as f:
                pdf_data = f.read()
                b64_data = base64.b64encode(pdf_data).decode("utf-8")
                pdf_url = f"data:application/pdf;base64,{b64_data}"
            
            return ui.tags.iframe(
                src=f"{pdf_url}#page={page}&zoom=100%",
                style="width: 900px; height: 600px; border: none;"
            )
        return ui.p("Error: Could not load original PDF")

    @output
    @render.ui
    def comparison_pdf_viewer():
        if not pdf_results.get()["has_compared"]:
            return ui.p("Please compare documents first to view PDFs")
        
        comp_path = pdf_results.get()["comparison_pdf_path"]
        page = current_page.get() 
        
        if comp_path and os.path.exists(comp_path):
            with open(comp_path, "rb") as f:
                pdf_data = f.read()
                b64_data = base64.b64encode(pdf_data).decode("utf-8")
                pdf_url = f"data:application/pdf;base64,{b64_data}"
            
            return ui.tags.iframe(
                src=f"{pdf_url}#page={page}&zoom=100%",
                style="width: 900px; height: 600px; border: none;"
            )
        return ui.p("Error: Could not load comparison PDF")   

    # Process PDFs and compute differences when the compare button is clicked
    @reactive.effect
    @reactive.event(input.compare_pdfs)
    def _():
        # Check if both PDFs are uploaded
        if not input.pdf_original() or not input.pdf_comparison():
            ui.notification_show("Please upload both PDF files for comparison", type="error")
            return
        
        try:
            # Extract text from both PDFs with per-page text
            original_text, original_path, original_by_page = extract_text_from_pdf(input.pdf_original()[0])
            comparison_text, comparison_path, comparison_by_page = extract_text_from_pdf(input.pdf_comparison()[0])
            
            # Compare the texts
            original_lines = original_text.splitlines()
            comparison_lines = comparison_text.splitlines()
            
            # Generate diff using difflib
            diff = difflib.unified_diff(
                original_lines, 
                comparison_lines, 
                lineterm='', 
                fromfile='Original', 
                tofile='Comparison'
            )
            diff_result = list(diff)
            
            # Calculate diff by page
            diff_by_page = {}
            max_pages = max(max(original_by_page.keys(), default=0), max(comparison_by_page.keys(), default=0))
            
            for page_num in range(1, max_pages + 1):
                orig_page_text = original_by_page.get(page_num, "")
                comp_page_text = comparison_by_page.get(page_num, "")
                
                page_diff = difflib.unified_diff(
                    orig_page_text.splitlines(),
                    comp_page_text.splitlines(),
                    lineterm='',
                    fromfile=f'Original Page {page_num}',
                    tofile=f'Comparison Page {page_num}'
                )
                diff_by_page[page_num] = list(page_diff)
            
            # Calculate statistics
            added_lines = sum(1 for line in diff_result if line.startswith('+') and not line.startswith('+++'))
            removed_lines = sum(1 for line in diff_result if line.startswith('-') and not line.startswith('---'))
            
            # Store results in the reactive value
            pdf_results.set({
                "text_diff": diff_result,
                "diff_by_page": diff_by_page,
                "has_compared": True,
                "original_pdf_path": original_path,
                "comparison_pdf_path": comparison_path,
                "original_text": original_text,
                "comparison_text": comparison_text,
                "original_by_page": original_by_page,
                "comparison_by_page": comparison_by_page,
                "summary": {
                    "added_lines": added_lines,
                    "removed_lines": removed_lines,
                    "total_changes": added_lines + removed_lines,
                    "original_name": input.pdf_original()[0]["name"],
                    "comparison_name": input.pdf_comparison()[0]["name"],
                    "max_pages": max_pages
                }
            })
            
            # Reset page navigation to start at page 1
            current_page.set(1)
            ui.update_numeric("goto_page", value=1, max=max_pages)
            
            ui.notification_show("PDF comparison complete", type="message")
            
        except Exception as e:
            ui.notification_show(f"Error comparing PDFs: {str(e)}", type="error")
    
    # Function to convert first page of PDF to base64 for display
    def get_pdf_thumbnail(pdf_path):
        """
        Extract the first page of a PDF as a base64 encoded image for display
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Base64 encoded string of the PDF's first page
        """
        try:
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                # Return the entire PDF file as base64
                pdf_data = f.read()
                return base64.b64encode(pdf_data).decode('utf-8')
        except Exception as e:
            print(f"Error getting PDF thumbnail: {str(e)}")
            return None

    # Render the visual differences between PDFs
    @output
    @render.ui
    def visual_diff_results():
        if not pdf_results()["has_compared"]:
            return ui.p("Click 'Compare Documents' to see a visual comparison of the PDFs.")
        
        original_path = pdf_results()["original_pdf_path"]
        comparison_path = pdf_results()["comparison_pdf_path"]
        
        if not original_path or not comparison_path:
            return ui.p("Error: PDF files not available for visual comparison.")
        
        # Get the PDF data as base64
        original_pdf = get_pdf_thumbnail(original_path)
        comparison_pdf = get_pdf_thumbnail(comparison_path)
        
        if not original_pdf or not comparison_pdf:
            return ui.p("Error: Could not generate PDF previews.")
            
        # Create a side-by-side view of the PDFs
        return ui.div(
            ui.h4(f"Visual Comparison", class_="text-center"),
            ui.p("Below are the PDF documents side by side for visual comparison. Use your browser's PDF viewer controls to navigate the pages."),
            ui.layout_columns(
                ui.card(
                    ui.card_header(f"Original: {pdf_results()['summary']['original_name']}"),
                    ui.tags.object(
                        ui.tags.data(src=f"data:application/pdf;base64,{original_pdf}"),
                        type="application/pdf",
                        width="100%",
                        height="600px",
                        style="border: 1px solid #ddd;"
                    )
                ),
                ui.card(
                    ui.card_header(f"Comparison: {pdf_results()['summary']['comparison_name']}"),
                    ui.tags.object(
                        ui.tags.data(src=f"data:application/pdf;base64,{comparison_pdf}"),
                        type="application/pdf",
                        width="100%",
                        height="600px",
                        style="border: 1px solid #ddd;"
                    )
                ),
                col_widths=[6, 6]
            )
        )
    
    #page differences output
    @output
    @render.ui
    def page_differences():
        if not pdf_results.get()["has_compared"]:
            return ui.p("Please compare documents first to view differences")
        
        page = current_page.get()
        diff_by_page = pdf_results.get()["diff_by_page"]
        max_pages = pdf_results.get()["summary"]["max_pages"]
        
        if page > max_pages:
            return ui.p("Page number exceeds document length")
        
        page_diffs = diff_by_page.get(page, [])
        if not page_diffs:
            return ui.p(f"No differences detected on page {page}")
        
        # Create a formatted HTML display of the differences
        diff_html = []
        for line in page_diffs:
            if line.startswith('+') and not line.startswith('+++'):
                diff_html.append(ui.tags.div(line, style="color: green; background-color: #e6ffe6;"))
            elif line.startswith('-') and not line.startswith('---'):
                diff_html.append(ui.tags.div(line, style="color: red; background-color: #ffe6e6;"))
            #elif line.startswith('@@'):
            #    diff_html.append(ui.tags.div(line, style="color: purple;"))
            #else:
            #    diff_html.append(ui.tags.div(line))
        
        return ui.card(
            ui.card_header(f"Differences on Page {page}"),
            ui.div(
                *diff_html,
                style="font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto;"
            )
        )




# Create the Shiny app
app = App(app_ui, server)
