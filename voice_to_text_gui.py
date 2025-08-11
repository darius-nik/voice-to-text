import os
import sys
import whisper
import threading
import time
from pathlib import Path
from typing import Optional

# Persian text utilities
try:
    from text_utils import normalize_persian, is_persian_text, shape_bidi_display
except Exception:
    # Fallbacks if utilities are unavailable
    def normalize_persian(text: str, *, convert_digits_to_persian: bool = True) -> str:  # type: ignore
        return text
    def is_persian_text(text: str) -> bool:  # type: ignore
        return False
    def shape_bidi_display(text: str) -> str:  # type: ignore
        return text

# Fix tkinter environment variables before importing
def fix_tkinter_env():
    """Set correct TCL/TK environment variables"""
    python_dir = os.path.dirname(sys.executable)
    
    # Check for system Python TCL/TK
    system_tcl_paths = [
        r"C:\Python313\tcl\tcl8.6",
        r"C:\Python312\tcl\tcl8.6", 
        r"C:\Python311\tcl\tcl8.6",
        r"C:\Python310\tcl\tcl8.6",
    ]
    
    system_tk_paths = [
        r"C:\Python313\tcl\tk8.6",
        r"C:\Python312\tcl\tk8.6",
        r"C:\Python311\tcl\tk8.6", 
        r"C:\Python310\tcl\tk8.6",
    ]
    
    # Find working TCL/TK
    for tcl_path, tk_path in zip(system_tcl_paths, system_tk_paths):
        if os.path.exists(tcl_path) and os.path.exists(tk_path):
            os.environ['TCL_LIBRARY'] = tcl_path
            os.environ['TK_LIBRARY'] = tk_path
            break

# Apply the fix before importing tkinter
fix_tkinter_env()

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
    TKINTER_AVAILABLE = True
except Exception as e:
    print(f"❌ tkinter error: {e}")
    TKINTER_AVAILABLE = False

# Try to import librosa for audio loading
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

class SimpleVoiceToTextGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ Voice to Text - OpenAI Whisper")
        self.root.geometry("700x500")
        self.root.configure(bg='#f5f5f5')
        
        # Initialize variables
        self.model = None
        self.model_cache = {}
        self.current_model_size: Optional[str] = None
        self.loader_win: Optional[tk.Toplevel] = None
        self.selected_file = None
        self.is_processing = False
        self._last_logical_text: Optional[str] = None  # for proper copy/save
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title_frame = tk.Frame(self.root, bg='#f5f5f5')
        title_frame.pack(pady=20)
        
        title_label = tk.Label(
            title_frame, 
            text="🎙️ Voice to Text Converter", 
            font=("Arial", 18, "bold"),
            bg='#f5f5f5',
            fg='#2c3e50'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame, 
            text="High-accuracy transcription using OpenAI Whisper", 
            font=("Arial", 10),
            bg='#f5f5f5',
            fg='#7f8c8d'
        )
        subtitle_label.pack()
        
        # Model selection
        model_frame = tk.Frame(self.root, bg='#f5f5f5')
        model_frame.pack(pady=15)
        
        tk.Label(
            model_frame, 
            text="🤖 Model Size:", 
            font=("Arial", 12, "bold"),
            bg='#f5f5f5',
            fg='#2c3e50'
        ).pack(side=tk.LEFT, padx=10)
        
        self.model_var = tk.StringVar(value="large")
        model_combo = ttk.Combobox(
            model_frame, 
            textvariable=self.model_var,
            values=["tiny (Fast)", "base (Balanced)", "small (Good)", "medium (Better)", "large (Best)"],
            state="readonly",
            width=20,
            font=("Arial", 10)
        )
        model_combo.pack(side=tk.LEFT, padx=10)
        model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        
        # File selection
        file_frame = tk.Frame(self.root, bg='#f5f5f5')
        file_frame.pack(pady=20)
        
        self.select_button = tk.Button(
            file_frame,
            text="📁 Select Audio File",
            command=self.select_file,
            font=("Arial", 12, "bold"),
            bg='#3498db',
            fg='white',
            padx=25,
            pady=12,
            cursor='hand2',
            relief='flat',
            borderwidth=0
        )
        self.select_button.pack(pady=5)
        
        self.file_label = tk.Label(
            file_frame,
            text="No file selected",
            font=("Arial", 10),
            bg='#f5f5f5',
            fg='#7f8c8d',
            wraplength=600
        )
        self.file_label.pack(pady=5)
        
        # Convert button
        self.convert_button = tk.Button(
            self.root,
            text="🚀 Convert to Text",
            command=self.convert_audio,
            font=("Arial", 14, "bold"),
            bg='#e74c3c',
            fg='white',
            padx=30,
            pady=15,
            cursor='hand2',
            state='disabled',
            relief='flat',
            borderwidth=0
        )
        self.convert_button.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.root,
            mode='indeterminate',
            length=500
        )
        self.progress.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Ready - Select an audio file to begin",
            font=("Arial", 10),
            bg='#f5f5f5',
            fg='#27ae60'
        )
        self.status_label.pack(pady=5)
        
        # Text output
        text_frame = tk.Frame(self.root, bg='#f5f5f5')
        text_frame.pack(pady=15, padx=20, fill='both', expand=True)
        
        tk.Label(
            text_frame,
            text="📝 Transcribed Text:",
            font=("Arial", 12, "bold"),
            bg='#f5f5f5',
            fg='#2c3e50',
            anchor='w'
        ).pack(fill='x', pady=(0, 5))
        
        self.text_output = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.CHAR,
            font=("Segoe UI", 11),
            bg='#ffffff',
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground='#e0e0e0',
            height=8
        )
        self.text_output.pack(fill='both', expand=True, padx=2, pady=2)
        # Improve line spacing for readability
        try:
            self.text_output.config(spacing1=4, spacing2=2, spacing3=4, insertwidth=2)
        except Exception:
            pass
        # Configure a tag for RTL/right-aligned text (for Persian output)
        try:
            self.text_output.tag_configure('rtl', justify='right', rmargin=8, lmargin1=8, lmargin2=8)
        except Exception:
            pass
        
        # Action buttons
        buttons_frame = tk.Frame(self.root, bg='#f5f5f5')
        buttons_frame.pack(pady=10)
        
        self.copy_button = tk.Button(
            buttons_frame,
            text="📋 Copy",
            command=self.copy_text,
            font=("Arial", 10),
            bg='#f39c12',
            fg='white',
            padx=15,
            pady=8,
            cursor='hand2',
            state='disabled',
            relief='flat',
            borderwidth=0
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(
            buttons_frame,
            text="💾 Save",
            command=self.save_text,
            font=("Arial", 10),
            bg='#9b59b6',
            fg='white',
            padx=15,
            pady=8,
            cursor='hand2',
            state='disabled',
            relief='flat',
            borderwidth=0
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(
            buttons_frame,
            text="🗑️ Clear",
            command=self.clear_text,
            font=("Arial", 10),
            bg='#95a5a6',
            fg='white',
            padx=15,
            pady=8,
            cursor='hand2',
            relief='flat',
            borderwidth=0
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
    
    def on_model_change(self, event):
        """Handle model size change"""
        selected = self.model_var.get()
        model_size = selected.split()[0]  # Extract model name (tiny, base, etc.)
        self.model = None  # Reset model to force reload
        self.current_model_size = model_size
        self.update_status(f"Model changed to {model_size} - loading...")
        # Preload selected model in a background thread with loader dialog
        t = threading.Thread(target=self._preload_model_thread, args=(model_size,), daemon=True)
        t.start()

    def _show_loader(self, message: str = "Loading..."):
        """Show a small modal loader window with an indeterminate progress bar."""
        if self.loader_win is not None:
            try:
                self.loader_win.destroy()
            except Exception:
                pass
            self.loader_win = None
        self.loader_win = tk.Toplevel(self.root)
        self.loader_win.title("Please wait")
        self.loader_win.configure(bg='#f5f5f5')
        self.loader_win.resizable(False, False)
        self.loader_win.transient(self.root)
        self.loader_win.grab_set()
        ttk.Label(self.loader_win, text=message).pack(padx=20, pady=(15, 5))
        p = ttk.Progressbar(self.loader_win, mode='indeterminate', length=240)
        p.pack(padx=20, pady=(0, 15))
        p.start(10)
        # center on parent
        try:
            self.loader_win.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (self.loader_win.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (self.loader_win.winfo_height() // 2)
            self.loader_win.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _hide_loader(self):
        if self.loader_win is not None:
            try:
                self.loader_win.destroy()
            except Exception:
                pass
            self.loader_win = None

    def _preload_model_thread(self, model_size: str):
        try:
            self.root.after(0, lambda: self._show_loader(f"Loading Whisper {model_size} model..."))
            # Use cache if already loaded
            if model_size in self.model_cache:
                self.model = self.model_cache[model_size]
            else:
                mdl = whisper.load_model(model_size)
                self.model_cache[model_size] = mdl
                self.model = mdl
            self.root.after(0, lambda: self.update_status(f"Model {model_size} ready"))
        except Exception as e:
            self.root.after(0, lambda: self._handle_error(f"Error loading model: {e}"))
        finally:
            self.root.after(0, self._hide_loader)
    
    def select_file(self):
        """Open file dialog to select audio file"""
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
            ("MP3 files", "*.mp3"),
            ("WAV files", "*.wav"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=filetypes
        )
        
        if filename:
            self.selected_file = filename
            file_name = os.path.basename(filename)
            self.file_label.config(text=f"Selected: {file_name}")
            self.convert_button.config(state='normal', bg='#27ae60')
            self.update_status("File selected - Ready to convert")
    
    def load_model(self, model_size):
        """Load Whisper model"""
        # Prefer cached model
        if model_size in self.model_cache:
            self.model = self.model_cache[model_size]
            return True
        if self.model is None:
            try:
                # Show loader during load
                self.root.after(0, lambda: self._show_loader(f"Loading Whisper {model_size} model..."))
                mdl = whisper.load_model(model_size)
                self.model_cache[model_size] = mdl
                self.model = mdl
                self.root.after(0, lambda: self.update_status(f"Model {model_size} loaded successfully"))
                return True
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Error loading model: {str(e)}"))
                messagebox.showerror("Model Error", f"Failed to load Whisper model: {str(e)}")
                return False
            finally:
                self.root.after(0, self._hide_loader)
        return True
    
    def convert_audio(self):
        """Convert audio to text using Whisper"""
        if not self.selected_file or self.is_processing:
            return
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self._convert_audio_thread)
        thread.daemon = True
        thread.start()
    
    def _convert_audio_thread(self):
        """Thread function for audio conversion"""
        try:
            self.is_processing = True
            self.root.after(0, self._start_processing_ui)
            
            # Get selected model
            selected = self.model_var.get()
            model_size = selected.split()[0]  # Extract model name
            
            # Load model
            if not self.load_model(model_size):
                return
            
            # Update status
            self.root.after(0, lambda: self.update_status("Transcribing audio..."))
            
            # Try transcription
            result = None
            try:
                # Direct Whisper transcription
                result = self.model.transcribe(
                    self.selected_file,
                    language=None,  # Auto-detect
                    task="transcribe",
                    verbose=False
                )
            except Exception as e:
                # Try with librosa if available
                if LIBROSA_AVAILABLE:
                    self.root.after(0, lambda: self.update_status("Trying alternative audio loading..."))
                    try:
                        audio, sr = librosa.load(self.selected_file, sr=16000)
                        result = self.model.transcribe(
                            audio,
                            language=None,
                            task="transcribe",
                            verbose=False
                        )
                    except Exception as e2:
                        raise Exception(f"Both methods failed: {str(e)}, {str(e2)}")
                else:
                    raise e
            
            if result:
                transcribed_text = result["text"].strip()
                detected_language = result.get("language", "unknown")
                
                # Update GUI with result
                self.root.after(0, lambda: self._display_result(transcribed_text, detected_language))
            else:
                raise Exception("No result from transcription")
            
        except Exception as e:
            error_msg = f"Error during transcription: {str(e)}"
            self.root.after(0, lambda: self._handle_error(error_msg))
        
        finally:
            self.is_processing = False
            self.root.after(0, self._stop_processing_ui)
    
    def _start_processing_ui(self):
        """Update UI for processing state"""
        self.convert_button.config(state='disabled', bg='#95a5a6')
        self.select_button.config(state='disabled')
        self.progress.start()
    
    def _stop_processing_ui(self):
        """Update UI after processing"""
        self.convert_button.config(state='normal', bg='#27ae60')
        self.select_button.config(state='normal')
        self.progress.stop()
    
    def _display_result(self, text, language):
        """Display transcription result"""
        # Decide if text is Persian
        maybe_persian = is_persian_text(text) or str(language).lower() in {"fa", "fas", "fa-ir", "persian"}
        if maybe_persian:
            logical = normalize_persian(text)
            visual = shape_bidi_display(logical)
            self._last_logical_text = logical
        else:
            visual = text
            self._last_logical_text = text

        self.text_output.delete(1.0, tk.END)
        if maybe_persian:
            # Insert visually-shaped RTL text and apply right alignment
            self.text_output.insert(1.0, visual, 'rtl')
        else:
            self.text_output.insert(1.0, visual)
        self.copy_button.config(state='normal')
        self.save_button.config(state='normal')
        self.update_status(f"✅ Transcription completed! Language: {language}")
    
    def _handle_error(self, error_msg):
        """Handle transcription errors"""
        self.update_status("❌ Transcription failed")
        messagebox.showerror("Transcription Error", error_msg)
    
    def copy_text(self):
        """Copy transcribed text to clipboard"""
        # Use logical text for clipboard to avoid copying shaped visual order
        text = (self._last_logical_text or self.text_output.get(1.0, tk.END)).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.update_status("Text copied to clipboard")
            messagebox.showinfo("Success", "Text copied to clipboard!")
    
    def save_text(self):
        """Save transcribed text to file"""
        # Save logical text to keep proper order for documents
        text = (self._last_logical_text or self.text_output.get(1.0, tk.END)).strip()
        if not text:
            messagebox.showwarning("Warning", "No text to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Transcription",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.update_status("Text saved successfully")
                messagebox.showinfo("Success", f"Text saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")
    
    def clear_text(self):
        """Clear the text output"""
        self.text_output.delete(1.0, tk.END)
        self.copy_button.config(state='disabled')
        self.save_button.config(state='disabled')
        self.update_status("Text cleared")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

def main():
    if not TKINTER_AVAILABLE:
        print("❌ tkinter is not available.")
        print("💡 Solutions:")
        print("1. Restart your PowerShell terminal")
        print("2. Reinstall Python with tkinter support")
        print("3. Use the command line version: python voice_to_text_working.py")
        return
    
    root = tk.Tk()
    app = SimpleVoiceToTextGUI(root)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Set minimum size
    root.minsize(600, 400)
    
    root.mainloop()

if __name__ == "__main__":
    main()
