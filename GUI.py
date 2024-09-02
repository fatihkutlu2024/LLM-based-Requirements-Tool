import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import threading
from Backend import *
from openai import OpenAI
from CTkTable import *

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("1250x600")
        self.title("Requirements LLM Tool")
        self._state_before_windows_set_titlebar_color = 'zoomed'

        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=0)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(5, weight=0)

        self.requirement_statuses = [] # Bool list for the selection of requirements
        self.selected_row = None
        self.table_content = None
        self.current_mode_process = None # Checks which operation should occur: change all with LLM, change selected with LLM, perform quality check with LLM
        self.selected_file_path = None
        self.server = None
        self.running = None
        self.completed_req_list = []
        self._reqif_loaded = False
        self.quality_control_percentage_number = 70

        self.changed_prompt = ""
        self.default_funct_prompt = """Reformulate the requirements into complete sentences in a prose-like manner while following this structure, using only the elements present in the original requirement. Do not add any new information that is not already included in the original requirement: 
1.  Conditional clause (only if the original requirement specifies a condition).
2.  The „system word“ (the subject in the sentence). Keep the system word unchanged.
3.  Use a modal verb ("shall," "should," "will"). If one is already in the sentence, keep it unchanged.
4.  Capability (e.g., "provide <actor> with the ability to," "be able to," or any other text as required).
5.  Process verb (if mentioned in the original requirement).
6.  Object (if mentioned in the original requirement).
Example: "If the user initiates a measurement within limits, the MRI system shall provide the user with the ability to start the measurement."
"""
        self.changed_percentage_prompt = ""
        self.default_percentage_prompt_criteria = """• Correctness: The requirement must be factually correct and technically verifiable.
• Unambiguity: The requirement should allow only one interpretation.
• Verifiability: The requirement must contain concrete and measurable statements to verify if it has been met.
• Modifiability: The requirement should be easily modifiable without needing extensive changes.
• Clarity: The requirement should be clear and understandable.
• Conciseness: The requirement should be as short as possible but as long as necessary.
• Avoidance of "Weak Words": The requirement should not contain weak or vague words."""

        self.requirement_information_prompt = f"Provide information on whether the requirement according to the criteria: {self.changed_percentage_prompt if self.changed_percentage_prompt else self.default_percentage_prompt_criteria}"


        self.sidebar_left_frame = ctk.CTkFrame(self,border_width=2, corner_radius=0, fg_color="#293241")
        self.sidebar_left_frame.grid(row=0, column=0, sticky="nsew", rowspan=5)
        self.sidebar_left_frame.grid_rowconfigure(0, weight=0, minsize=40)
        self.sidebar_left_frame.grid_rowconfigure(1, weight=0)
        self.sidebar_left_frame.grid_rowconfigure(2, weight=0)
        self.sidebar_left_frame.grid_rowconfigure(3, weight=1)
        self.sidebar_left_frame.grid_rowconfigure(4, weight=1)
        self.sidebar_left_frame.grid_rowconfigure(5, weight=0)
        self.sidebar_left_frame.grid_rowconfigure(6, weight=0)
        self.sidebar_left_frame.grid_rowconfigure(7, weight=0)
        self.sidebar_left_frame.grid_rowconfigure(8, weight=0, minsize=100)

        self.upload = ctk.CTkButton(self.sidebar_left_frame, height=30, width=150, font=(None,15), text="Upload", command=self.load_reqif)
        self.upload.grid(row=1, column=0, padx=20, pady=(30,10))

        self.save_button = ctk.CTkButton(self.sidebar_left_frame, height=30, width=150, font=(None,15), text="Save", command=self.save_file, state="disabled")
        self.save_button.grid(row=2, column=0, padx=20, pady=10)

        self.optionmenu_1 = ctk.CTkOptionMenu(self.sidebar_left_frame, height=30, width=150, font=(None,15), values=["GPT-4o","GPT-3.5 Turbo","Meta Llama 3 8B Instruct","Claude 3.5 Sonnet","Gemini Pro 1.5","Google Gemma 2 9B","Yi Large","Mistral 7B Instruct","WizardLM-2 8x22B","Qwen2-72B-Instruct"], command=self.option_selected)
        self.optionmenu_1.grid(row=3, column=0, padx=20, pady=30,sticky="s")
        self.optionmenu_1.set("Select LLM")

        self.separator = ctk.CTkFrame(self.sidebar_left_frame, height=2, fg_color="#D1D5DB", width=200)
        self.separator.grid(row=4, column=0, padx=10, pady=(10, 10), sticky="ew")

        self.prompt_label = ctk.CTkLabel(self.sidebar_left_frame, text="Configuration\nPrompts", font=(None,20))
        self.prompt_label.grid(row=5, column=0, sticky="ew", pady=10, padx=10)

        self.reformulation_prompt_button = ctk.CTkButton(self.sidebar_left_frame, height=40, corner_radius=20, text="Reformulation Prompt",font=(None,15), command=lambda: self.open_text_window("reformulation"))
        self.reformulation_prompt_button.grid(row=6, column=0, sticky="", pady=10, padx=10)

        self.quality_control_prompt_Button = ctk.CTkButton(self.sidebar_left_frame, height=40, corner_radius=20, font=(None,15), text="Quality Control Prompt", command=lambda: self.open_text_window("percentage"))
        self.quality_control_prompt_Button.grid(row=7, column=0, sticky="", pady=10, padx=10)

        self.top_frame = ctk.CTkFrame(self, fg_color="#293241", border_width=2, corner_radius=0)
        self.top_frame.grid(row=0, column=1, sticky="nsew", columnspan=4)
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(4, weight=1)

        self.title_label = ctk.CTkLabel(self.top_frame, text="Requirements LLM Tool", font=ctk.CTkFont(size=25, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=(20, 0), pady=20, sticky="w")

        self.start_button = ctk.CTkButton(self.top_frame, text="Start",corner_radius=30, height=60, width=170, font=(None,18), fg_color="#006400", border_color="green", border_width=2, hover_color="#004d00", command=lambda: self.start_process_thread("change_complete_table"))
        self.start_button.grid(row=0, column=2,padx=10, pady=20, sticky="e")

        self.control_quality_Button = ctk.CTkButton(self.top_frame, text="Quality Check", corner_radius=30, height=60, width=170, font=(None,18), fg_color="#0056b3", command=lambda: self.start_process_thread("do_quality_check"))
        self.control_quality_Button.grid(row=0, column=3,padx=10, pady=20)

        self.stop_button = ctk.CTkButton(self.top_frame, text="Stop", height=60, width=150, corner_radius=30, font=(None,18), border_color="red", border_width=1,fg_color="#3F3F3F", hover_color="#870F1A", state="disabled", command=self.stop_process)
        self.stop_button.grid(row=0, column=4,padx=10, pady=20, sticky='w')

        self.table_frame = ctk.CTkFrame(self, corner_radius=10)
        self.table_frame.grid(row=1, column=1, sticky="nsew", columnspan=4)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        self.table_frame_sidebar_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_frame_sidebar_frame.grid(row=0, column=1, rowspan=10, sticky="nsew")
        self.table_frame_sidebar_frame.grid_rowconfigure(0, weight=0, minsize=200)
        self.table_frame_sidebar_frame.grid_rowconfigure(3, weight=1)
        self.table_frame_sidebar_frame.grid_columnconfigure(0, minsize=20)

        self.progressbar = ctk.CTkProgressBar(self, orientation="horizontal", width=700)
        self.progressbar.grid(row=2, column=1, padx=10, pady=20, columnspan=2)
        self.progressbar.set(0)

        self.placeholder_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0, width=180, height=0)
        self.placeholder_frame.grid(row=2, column=4, sticky="ew")

        self.original_requirement_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#346789", height=70)
        self.original_requirement_frame.grid(row=3, column=1, padx=5, pady=10, sticky="nsew", columnspan=3)

        self.original_requirement_label = ctk.CTkLabel(self.original_requirement_frame, text="Original Requirement:", corner_radius=10)
        self.original_requirement_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.original_requirement_col_2_label = ctk.CTkLabel(self.original_requirement_frame,text=f"",wraplength=900)
        self.original_requirement_col_2_label.grid(row=0, column=1, pady=10, sticky="w")

        self.get_information_frame = ctk.CTkFrame(self, fg_color="#293241")
        self.get_information_frame.grid(row=4, column=1, columnspan=4, sticky="nsew", padx=5)
        self.get_information_frame.grid_columnconfigure(0, weight=1)

        self.get_information_button = ctk.CTkButton(self.get_information_frame, text="Get Information", font=(None,15), state="disabled", command=self.get_requirement_information)
        self.get_information_button.grid(row=0, column=0, padx=10, pady=(20,10), sticky="w")

        self.req_information_frame = ctk.CTkFrame(self.get_information_frame, height=70, fg_color="#346789")
        self.req_information_frame.grid(row=1, column=0, padx=5, pady=10, sticky="nsew", columnspan=3)
        self.req_information_frame.grid_propagate(False)

        self.requirement_information_label = ctk.CTkLabel(self.req_information_frame, text="", wraplength=1300, font=(None,14))
        self.requirement_information_label.grid(row=0, column=0, padx=(10,10))

    def deselect_current_row(self): # Deselect the currently selected row in the table.
        if self.selected_row:
            self.table.deselect_row(self.selected_row)
            self.selected_row = None

    def get_requirement_information(self): # Get detailed information about the selected requirement.
        if self.selected_row:
            information_text = process_requirement(self.server[0], self.server[1], self.table_content[self.selected_row][0], self.requirement_information_prompt, "get_information")
            self.requirement_information_label.configure(text=information_text)

    def remove_status_values(self): # Reset the status values of all requirements.
        self.deselect_current_row()
        if self.requirement_statuses:
            self.requirement_statuses=(len(self.original_document)*[False])
            self.table.edit_column(2,"")
            self.table.insert(row=0, column=2, value="Status")
            self.start_button.configure(text="Start", command=lambda: self.start_process_thread("change_complete_table"))

    def cell_clicked(self, data): # Selects the line in the table and displays the original request.
        if self.selected_row: # If cell has been clicked, visually cancel selection
            self.table.deselect_row(self.selected_row)

        self.selected_row = data['row']
        self.table.select_row(self.selected_row)
        text = self.original_document[self.selected_row - 1] if self.selected_row != 0 else ""
        self.original_requirement_col_2_label.configure(text=text)

    def edit_requirement_maunally(self): # Allow manual editing of the selected requirement.
        if self.selected_row:
            current_value = self.table.get(row=self.selected_row, column=0)
            new_value = simpledialog.askstring("change cell value", f"current value : {current_value}\n\nnew value:", initialvalue=current_value)
            
            if new_value is not None and new_value != current_value:
                self.table.insert(row=self.selected_row, column=0, value=new_value)
                self.table_content[self.selected_row][0]= new_value

                if self.table.get(self.selected_row,2) == "❌":
                    self.requirement_statuses[self.selected_row-1] = False
                    self.table.insert(row=self.selected_row, column=1, value="-")
                    self.table.insert(row=self.selected_row, column=2, value="✓",text_color="green",font=(None,19))
            self.control_status()
                    
    def control_status(self): # Update the status of the start button based on the requirement statuses.
        if any(self.requirement_statuses):
            self.start_button.configure(text="Edit Selected: Start",command=lambda: self.start_process_thread("change_selected_reqirements"))
        else:
            self.start_button.configure(text="Start",command=lambda: self.start_process_thread("change_complete_table"))

    def switch_requirement_status(self):
        if self.selected_row:
            current_state = self.requirement_statuses[self.selected_row-1]
            if current_state: 
                new_state = False
            else:
                new_state = True
            self.requirement_statuses[self.selected_row-1] = new_state
            symbol = "❌" if new_state else "✓"
            text_color = "red" if new_state else "green"
            font_size = (None, 16) if new_state else (None, 19)
            self.table.insert(row=self.selected_row, column=2, value=symbol, text_color=text_color, font=font_size)
            self.control_status()

    def option_selected(self, model): # Selection of LLMs
        self.deselect_current_row()
        self.get_information_button.configure(state="normal")

        if model == "GPT-4o":
            openai.api_key = "API-KEY"
            self.server = (openai, "gpt-4o")
        elif model == "GPT-3.5 Turbo":
            openai.api_key = "API-KEY"
            self.server = (openai, "gpt-3.5-turbo-0125")
        elif model == "Mistral 7B Instruct":
            client = OpenAI(api_key="API-KEY",base_url="https://api.deepinfra.com/v1/openai")
            self.server = (client, "mistralai/Mistral-7B-Instruct-v0.3")
        elif model == "Mixtral 8x7B Instruct":
            client = OpenAI(api_key="API-KEY",base_url="https://api.deepinfra.com/v1/openai")
            self.server = (client, "mistralai/Mixtral-8x7B-Instruct-v0.1")
        elif model == "Qwen2-72B-Instruct":
            client = OpenAI(api_key="API-KEY",base_url="https://api.deepinfra.com/v1/openai")
            self.server = (client, "Qwen/Qwen2-72B-Instruct")
        elif model == "Meta Llama 3 8B Instruct":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "meta-llama/llama-3-8b-instruct")
        elif model == "Claude 3.5 Sonnet":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "anthropic/claude-3.5-sonnet")
        elif model == "Gemini Pro 1.5":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "google/gemini-pro-1.5")
        elif model == "Yi Large":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "01-ai/yi-large")
        elif model == "Mistral: Mistral 7B Instruct":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "mistral/mistral-7b-instruct")
        elif model == "Mixtral 8x7B Instruct":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "mixtral/mixtral-8x7b-instruct")
        elif model == "WizardLM-2 8x22B":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "microsoft/wizardlm-2-8x22b")
        elif model == "Google Gemma 2 9B":
            client = OpenAI(api_key="sk-or-v1-API-KEY", base_url="https://openrouter.ai/api/v1")
            self.server = (client, "google/gemma-2-9b-it")

    def start_process_thread(self,mode):# Updating the GUI is only possible with the thread function
        self.current_mode_process = mode
        thread = threading.Thread(target=self.start_process)
        thread.start()

    def start_process(self): # start main process (reformulation, quality control, get information about the requirement)
        self.deselect_current_row()
        if self.selected_file_path == None:
            messagebox.showerror("Error", "ReqIF file was not selected")
            return
        if self.server == None:
            messagebox.showerror("Error", "Please select an LLM first.")
            return

        self.configure_button_status("disabled")
        self.stop_button.configure(state="normal",fg_color="#D1001C")
        self.running = True

        if self.current_mode_process == "change_complete_table":            
            for counter, requirement in enumerate(self.table_content[1:],start=1):
                response = process_requirement(self.server[0], self.server[1], requirement[0], self.changed_prompt if self.changed_prompt else self.default_funct_prompt, None)
                self.table_content[counter][0] = response
                self.table.insert(row=counter, column=0, value=response)
                self.table.insert(row=counter, column=1, value="-")
                self.update_progress_bar(counter+1, len(self.table_content))
                if not self.running:
                    break

        elif self.current_mode_process == "do_quality_check":
            quality_control_prompt= f"Your task is to provide a percentage that indicates whether the requirement is well written or not, based on the following criteria:{self.changed_percentage_prompt if self.changed_percentage_prompt else self.default_percentage_prompt_criteria}\nProvide a number as a result under any circumstances."

            for counter, requirement in enumerate(self.table_content[1:], start=1):
                percentage = process_requirement(self.server[0], self.server[1], requirement[0],quality_control_prompt, "quality_control")
                self.table.insert(row=counter, column=1, value=percentage[:2])
                self.update_progress_bar(counter+1, len(self.table_content))

                if int(percentage[:2]) < self.quality_control_percentage_number: 
                    self.requirement_statuses[counter-1] = True
                    self.table.insert(row=counter, column=2, value="❌", text_color="red", font=(None,16))
                else:
                    self.requirement_statuses[counter-1] = False
                    self.table.insert(row=counter, column=2, value="✓", text_color="green", font=(None,19))
                if not self.running:
                    break
            self.control_status()

        elif self.current_mode_process == "change_selected_reqirements":
            for index, bool_value in enumerate(self.requirement_statuses):
                if bool_value:    
                    response = process_requirement(self.server[0], self.server[1], self.table_content[index+1][0], self.changed_prompt if self.changed_prompt else self.default_funct_prompt, None)
                    self.table.insert(row=index+1, column=0, value=response)
                    self.table.insert(row=index+1, column=1, value="-")
                    self.table.insert(row=index+1, column=2, value="✓", text_color="blue", font=(None,19))
                    self.table_content[index+1][0] = response
                    self.requirement_statuses[index] = False
                self.update_progress_bar(index+1, len(self.table_content))
                if not self.running:
                    break
            if not any(self.requirement_statuses):
                self.start_button.configure(text="Start",command=lambda: self.start_process_thread("change_complete_table"))
        
        self.deselect_current_row()
        self.progressbar.set(0)
        self.configure_button_status("normal")
        self.stop_button.configure(state="disabled", fg_color="#3F3F3F")

    def stop_process(self): # stops the process
        self.running = False

    def configure_button_status(self, current_status):
        self.start_button.configure(state=current_status)
        self.upload.configure(state=current_status)
        self.save_button.configure(state=current_status)
        self.optionmenu_1.configure(state=current_status)
        self.reformulation_prompt_button.configure(state=current_status)
        self.quality_control_prompt_Button.configure(state=current_status)
        self.remove_status_values_button.configure(state=current_status)
        self.set_status_button.configure(state=current_status)
        self.edit_req_button.configure(state=current_status)
        self.get_information_button.configure(state=current_status)
        self.control_quality_Button.configure(state=current_status)

    def save_file(self):
        self.deselect_current_row()
        self.completed_req_list = self.table.get_column(column=0)[1:]
        output_file_path = filedialog.asksaveasfilename(defaultextension=".reqif", filetypes=[("ReqIF file", "*.reqif")], title="Save as")
        if output_file_path:
            update_reqif_requirements(self.selected_file_path, self.completed_req_list, output_file_path, self.reqs_column_index)
        else:
            return

    def load_reqif(self):
        self.deselect_current_row()
        self.selected_file_path = filedialog.askopenfilename(title="Select ReqIF file", filetypes=[("ReqIF files", "*.reqif")])
        if self.selected_file_path:
            self.reqif_loaded = True
            self.save_button.configure(state="normal")

    @property
    def reqif_loaded(self):
        return self._reqif_loaded

    @reqif_loaded.setter
    def reqif_loaded(self, value): 
        self._reqif_loaded = value
        if self._reqif_loaded:
            if hasattr(self, 'table_scrollable'):
                self.table_scrollable.destroy()
            
            self.original_document,self.reqs_column_index = extract_reqif_requirements(self.selected_file_path)
            if self.reqs_column_index is None:
                messagebox.showerror("Error", "Column with the requirements not found.\n\n\nNote:\nColumn name must be 'Requirement' or 'Requirements'")
            self.table_content = [["Requirements", "%","Status"]] + [[data,"-",""] for data in self.original_document]
            self.requirement_statuses = (len(self.original_document)*[False])
            self.start_button.configure(text="Start", command=lambda: self.start_process_thread("change_complete_table"))

            self.table_scrollable = ctk.CTkScrollableFrame(self.table_frame, fg_color="black")
            self.table_scrollable.grid(row=0, column=0, sticky="nsew")
            self.table_scrollable.grid_rowconfigure(0, weight=1)
            self.table_scrollable.grid_columnconfigure(0, weight=1)

            self.table = CTkTable(self.table_scrollable, colors=["#1a1a1f", "#000000"], width=1, font=(None,14), header_color="#2A8C55", hover_color="#555D50", values=self.table_content, command=self.cell_clicked)
            self.table.grid(row=0, column=0, sticky="nsew")
            self.table.edit_row(0, height=40, font=(None,18))

            self.edit_req_button = ctk.CTkButton(self.table_frame_sidebar_frame, font=(None,15), text="Edit", command=self.edit_requirement_maunally)
            self.edit_req_button.grid(row=1, column=1, sticky="nsew", pady=10, padx=10)
            
            self.set_status_button = ctk.CTkButton(self.table_frame_sidebar_frame, font=(None,15), text="Set status", command=self.switch_requirement_status)
            self.set_status_button.grid(row=2, column=1, sticky="nsew", pady=10, padx=10)

            self.remove_status_values_button = ctk.CTkButton(self, text="Remove status values", command=self.remove_status_values)
            self.remove_status_values_button.grid(row=2, column=3, pady=(10,0), sticky='w')

    def update_progress_bar(self, current, total):
        progress = current/ total
        self.progressbar.set(progress)
        self.update_idletasks()

    def open_text_window(self,prompt_type):
        self.deselect_current_row()

        self.text_window = ctk.CTkToplevel(self)
        title = "Reformulation Prompt" if prompt_type == "reformulation" else "Quality Control Prompt"
        self.text_window.title(title)
        self.text_window.geometry("485x305")

        textbox_content = ""
        if prompt_type == "reformulation":
            textbox_content = self.changed_prompt if self.changed_prompt else self.default_funct_prompt
            buttons_row = 2

        elif prompt_type == "percentage":
            self.text_window.geometry("485x395")
            textbox_content = self.changed_percentage_prompt if self.changed_percentage_prompt else self.default_percentage_prompt_criteria

            self.default_percentage_label_tw = ctk.CTkLabel(
                    self.text_window,text="Your task is to provide a percentage that indicates whether the request is well written or not, based on the following criteria:",
                    fg_color="transparent", corner_radius=15, wraplength=460, anchor="w", justify="left")
            self.default_percentage_label_tw.grid(row=0, column=0, columnspan=3, padx=10, pady=(15, 5), sticky="w")

            self.quality_prompt_fixed_text = ctk.CTkLabel(self.text_window, text="Threshold for 'good':", anchor="e", padx=10, pady=10)
            self.quality_prompt_fixed_text.grid(row=2, column=0, sticky="e")

            self.set_percentage_entry = ctk.CTkEntry(self.text_window, width=120, corner_radius=10)
            self.set_percentage_entry.grid(row=2, column=1, sticky="w")
            self.set_percentage_entry.insert(0, self.quality_control_percentage_number)

            buttons_row = 3

        self.textbox = ctk.CTkTextbox(self.text_window, width=400, height=230, corner_radius=10, wrap="word")
        self.textbox.grid(row=1, column=0, columnspan=3, padx=10, pady=(10,10))
        self.textbox.insert("0.0", textbox_content)

        self.default_button = ctk.CTkButton(self.text_window, text="default prompt", command=lambda: self.reset_to_default(prompt_type))
        self.ok_button = ctk.CTkButton(self.text_window, text="save all", command=lambda: self.save_text(prompt_type))
        self.cancel_button = ctk.CTkButton(self.text_window, text="close", command=self.cancel)

        self.ok_button.grid(row=buttons_row, column=0, pady=10, padx=10)
        self.default_button.grid(row=buttons_row, column=1, pady=10, padx=10, sticky="w")
        self.cancel_button.grid(row=buttons_row, column=2, pady=10, padx=10, sticky="e")

        self.text_window.focus_force() # Window is placed in the foreground
        self.text_window.grab_set() # Blocks everything as long as the window is not closed

    def save_text(self, prompt_type):
        changed_text = self.textbox.get("0.0", "end").strip()

        if prompt_type == "reformulation":
            self.changed_prompt = changed_text
            self.text_window.destroy()
        else:
            new_percentage_value = self.set_percentage_entry.get().strip()

            if not new_percentage_value.isdigit():
                messagebox.showerror("Error", "The input must be a positive integer.")
                return
            if not 0 <= int(new_percentage_value) <= 100:
                messagebox.showerror("Error", "The number must be between 0 and 100.")
                return

            self.changed_percentage_prompt = changed_text if changed_text != self.default_percentage_prompt_criteria else ""
            self.quality_control_percentage_number = int(new_percentage_value)
        self.text_window.destroy()

    def reset_to_default(self, prompt_type):
        self.textbox.delete("0.0", "end")
        
        if prompt_type == "reformulation":
            self.textbox.insert("0.0", self.default_funct_prompt)
        else:
            self.textbox.insert("0.0", self.default_percentage_prompt_criteria)

    def cancel(self):
        self.text_window.destroy()

app = App()
app.mainloop()