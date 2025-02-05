import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkthemes import ThemedTk
import requests
import threading
import time

class AINotePad:
    def __init__(self):
        self.root = ThemedTk(theme="arc")
        self.root.title("AI Notepad")
        self.root.geometry("900x600")

        # Configure main container with grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create main frame with modern styling
        self.main_frame = ttk.Frame(self.root, padding=(10, 10), relief="flat")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Create text area with scrollbar
        self.text_area = tk.Text(
            self.main_frame,
            wrap=tk.WORD,
            undo=True,
            font=('Helvetica', 12),
            bg='#F5F5F5',  # Light gray background
            fg='#333333',  # Dark text
            insertbackground='black',  # Cursor color
            bd=0,  # No border
            highlightthickness=0  # No highlight border
        )
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient='vertical', command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=self.scrollbar.set)
        
        # Grid layout
        self.text_area.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Create suggestion popup
        self.suggestion_window = tk.Toplevel(self.root)
        self.suggestion_window.withdraw()  # Hide initially
        self.suggestion_window.overrideredirect(True)  # Remove window decorations
        
        # Suggestion text in popup
        self.suggestion_text = ttk.Label(
            self.suggestion_window,
            text="",
            font=('Helvetica', 11),
            background='#FFFFFF',  # White background
            foreground='#333333',  # Dark text
            padding=(5, 5)
        )
        self.suggestion_text.pack(fill=tk.X)

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W, relief=tk.SUNKEN, padding=(5, 5))
        self.status_bar.grid(row=1, column=0, sticky="ew")

        # Create menu
        self.create_menu()

        # Ollama API settings
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "deepseek-r1:1.5b"  # Default model
        self.last_request_time = 0
        self.suggestion_delay = 0.5  # Delay in seconds
        self.last_text = ""
        self.suggestion_thread = None

        # Bind events
        self.text_area.bind('<KeyRelease>', self.handle_keypress)
        self.text_area.bind('<Tab>', self.accept_suggestion)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Cut", command=lambda: self.text_area.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.text_area.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.text_area.event_generate("<<Paste>>"))

        # AI Menu
        ai_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Model", menu=ai_menu)
        ai_menu.add_command(label="Change Model", command=self.change_model)

    def new_file(self):
        self.text_area.delete(1.0, tk.END)
        self.status_bar.config(text="New File")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(1.0, file.read())
                self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Couldn't open file: {str(e)}")

    def save_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    file.write(self.text_area.get(1.0, tk.END))
                self.status_bar.config(text=f"Saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Couldn't save file: {str(e)}")

    def change_model(self):
        models = ["tinyllama", "mistral", "llama2", "codellama", "gemma", "qwen", "qwen2", "phi3", "llama3", "gemma2", "codellama"]
        dialog = tk.Toplevel(self.root)
        dialog.title("Select AI Model")
        dialog.geometry("200x250")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Choose a model:").pack(pady=10)
        
        var = tk.StringVar(value=self.model)
        for model in models:
            ttk.Radiobutton(dialog, text=model, variable=var, value=model).pack(pady=5)

        def on_select():
            self.model = var.get()
            self.status_bar.config(text=f"Model changed to: {self.model}")
            dialog.destroy()

        ttk.Button(dialog, text="Select", command=on_select).pack(pady=10)

    def get_ai_suggestion(self, text):
        try:
            self.status_bar.config(text="Getting AI suggestion...")
            print("\n--- Getting AI Suggestion ---")
            
            words = text.split()
            context = ' '.join(words[-10:]) if len(words) > 10 else text
            
            prompt = f"Complete this sentence (3-5 words only): {context}"
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 30
                }
            }
            
            print(f"Sending request to Ollama...")
            response = requests.post(
                self.ollama_url, 
                json=data, 
                timeout=3
            )
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                suggestion = result.get('response', '').strip()
                print(f"Suggestion received: '{suggestion}'")
                # Use after to delay the update
                self.root.after(100, lambda: self.update_suggestion(suggestion))  # Delay of 100 ms
                self.status_bar.config(text="Ready")
            else:
                error_msg = f"API Error: {response.status_code}"
                print(f"Error: {error_msg}")
                self.root.after(0, lambda: self.update_suggestion(f"(Error: {error_msg})"))
                self.status_bar.config(text=error_msg)
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. Trying again..."
            print(error_msg)
            self.status_bar.config(text=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Ollama. Is it running?"
            print(f"Error: {error_msg}")
            self.root.after(0, lambda: self.update_suggestion(f"(Error: {error_msg})"))
            self.status_bar.config(text=error_msg)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"Exception occurred: {error_msg}")
            self.root.after(0, lambda: self.update_suggestion(f"({error_msg})"))
            self.status_bar.config(text=error_msg)

    def update_suggestion(self, text):
        print(f"Updating UI with suggestion: '{text}'")
        if not text or text.startswith('(Error'):
            self.suggestion_window.withdraw()
            return

        try:
            cursor_pos = self.text_area.index(tk.INSERT)
            bbox = self.text_area.bbox(cursor_pos)
            
            if bbox:
                x, y, _, h = bbox
                
                text_x = self.text_area.winfo_rootx()
                text_y = self.text_area.winfo_rooty()
                
                # Position popup below the cursor
                popup_x = text_x + x + 5
                popup_y = text_y + y + h + 5  # Adjust to position below the cursor

                self.suggestion_text['text'] = text
                
                self.suggestion_window.geometry(f"+{popup_x}+{popup_y}")
                self.suggestion_window.deiconify()
                self.suggestion_window.lift()
            else:
                self.suggestion_window.withdraw()
        except Exception as e:
            print(f"Error updating UI: {e}")
            self.suggestion_window.withdraw()

    def handle_keypress(self, event):
        if not event.char or not event.char.isprintable():
            return
            
        current_time = time.time()
        if current_time - self.last_request_time >= self.suggestion_delay:
            self.last_request_time = current_time
            
            current_text = self.text_area.get("1.0", "end-1c").strip()
            
            if len(current_text) > 0:
                if self.suggestion_thread and self.suggestion_thread.is_alive():
                    self.suggestion_thread = None
                
                self.suggestion_thread = threading.Thread(
                    target=self.get_ai_suggestion,
                    args=(current_text,)
                )
                self.suggestion_thread.daemon = True
                self.suggestion_thread.start()

    def accept_suggestion(self, event):
        if self.suggestion_window.winfo_viewable():
            suggestion = self.suggestion_text['text']
            if suggestion and not suggestion.startswith('(Error'):
                self.text_area.insert(tk.INSERT, suggestion)
                self.suggestion_window.withdraw()
                return "break"
        return None

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AINotePad()
    app.run()