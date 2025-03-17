import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from googletrans import Translator
import pyttsx3
import time
import keyboard
import pyautogui
from PIL import ImageGrab
import pytesseract
import logging
import os
import json
import threading
from cryptography.fernet import Fernet
from logging.handlers import RotatingFileHandler

# Configuração do logger
logger = logging.getLogger('TranslatorApp')
def setup_logging():
    try:
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_file = 'translator.log'
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        handler.setFormatter(log_formatter)
        
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        
        # Adicionar handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
        
    except Exception as e:
        print(f"Erro ao configurar logging: {str(e)}")

setup_logging()

# Verificação de dependências
def check_dependencies():
    required_packages = {
        'cryptography': 'pip install cryptography',
        'pillow': 'pip install pillow',
        'pytesseract': 'pip install pytesseract',
        'pyttsx3': 'pip install pyttsx3',
        'googletrans': 'pip install googletrans==3.1.0a0',
        'keyboard': 'pip install keyboard'
    }
    
    missing_packages = []
    for package, install_cmd in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(f"{package} ({install_cmd})")
    
    if missing_packages:
        error_msg = "Pacotes necessários não encontrados:\n\n" + "\n".join(missing_packages)
        messagebox.showerror("Erro de Dependências", error_msg)
        exit(1)

# Configuração do Tesseract
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception as e:
    messagebox.showerror("Erro", "Tesseract não encontrado. Por favor, instale o Tesseract-OCR.")
    exit(1)

# Variáveis globais
resultado_janela = None
label_resultado = None
fechar_automaticamente = False
tempo_fechamento = 10
menu_aberto = False
tema_escuro = True
traducao_em_tempo_real = False
ultima_traducao = ""
intervalo_atualizacao = 1.0
movendo = False
redimensionando = False
pos_x = 0
pos_y = 0
class SecurityManager:
    def __init__(self):
        self.key = self._load_or_create_key()
        self.cipher_suite = Fernet(self.key)
        
    def _load_or_create_key(self):
        key_file = 'secret.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_data(self, data):
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data):
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

class RateLimiter:
    def __init__(self, max_requests=60, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_proceed(self):
        current_time = time.time()
        # Remove requests mais antigos que time_window
        self.requests = [req for req in self.requests 
                        if current_time - req < self.time_window]
        
        # Verifica se ainda pode fazer mais requisições
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False

class SpeechManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.is_speaking = False
        self.voice_enabled = True
        self.current_voice = 'pt'
        self._load_voices()

    def _load_voices(self):
        self.available_voices = {}
        voice_names = {
            'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_PT-BR_MARIA_11.0': 'Maria (Português)',
            'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_DAVID_11.0': 'David (English)',
            'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_ZIRA_11.0': 'Zira (English)'
        }
        
        for voice in self.engine.getProperty('voices'):
            friendly_name = voice_names.get(voice.id, voice.name)
            self.available_voices[friendly_name] = voice

    def set_voice(self, friendly_name):
        if friendly_name in self.available_voices:
            voice = self.available_voices[friendly_name]
            self.engine.setProperty('voice', voice.id)
            self.current_voice = friendly_name
            self.engine.setProperty('rate', 180)
            self.engine.setProperty('volume', 1.0)

    def _preprocess_text(self, text):
        text = text.replace(".", ". ").replace("!", "! ").replace("?", "? ")
        text = text.replace("\n", " ")
        return ' '.join(text.split())

    def speak(self, text):
        if not self.voice_enabled:
            return
        if self.is_speaking:
            self.stop()
        
        try:
            self.engine.setProperty('rate', 180)
            self.engine.setProperty('volume', 1.0)
            
            processed_text = self._preprocess_text(text)
            sentences = processed_text.split('. ')
            
            self.is_speaking = True
            for sentence in sentences:
                if sentence.strip():
                    self.engine.say(sentence.strip())
                    self.engine.runAndWait()
                    if len(sentences) > 1:
                        time.sleep(0.3)
        finally:
            self.is_speaking = False

    def stop(self):
        if self.is_speaking:
            self.engine.stop()
            self.is_speaking = False

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        return self.voice_enabled

class TranslationWindow:
    def __init__(self, translation_text):
        self.root = tk.Toplevel()  # Alterado de Tk para Toplevel
        self.root.title("Tradução")
        
        # Configurar a janela
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Calcular posição para centralizar
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 400
        window_height = 200
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Área de texto com scrollbar
        self.text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            width=40,
            height=8,
            font=('Arial', 12)
        )
        
        # Adicionar scrollbar
        scrollbar = tk.Scrollbar(main_frame, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        self.text_widget.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        self.text_widget.insert(tk.END, translation_text)
        self.text_widget.configure(state='disabled')
        
        # Botão de fechar
        close_button = tk.Button(
            main_frame,
            text="Fechar",
            command=self.close_window,
            bg='#ff4444',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        close_button.pack(pady=(0, 10))
        
        # Bindings para fechar a janela
        self.root.bind('<Button-1>', self.close_window)
        self.root.bind('<Key>', self.close_window)
        self.text_widget.bind('<Button-1>', self.close_window)
        close_button.bind('<Button-1>', self.close_window)
        
        # Protocolo de fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
    
    def close_window(self, event=None):
        try:
            if self.root:
                self.root.destroy()
        except:
            pass
    
    def show(self):
        try:
            self.root.mainloop()
        except:
            pass

class SecureTranslator:
    def __init__(self):
        self.security = SecurityManager()
        self.speech = SpeechManager()
        self.translator = Translator()
        self.last_translation = ""
        self.last_translation_time = None
        self.rate_limiter = RateLimiter()
    
    def translate_and_speak(self, text):
        try:
            if not text:
                return None
                
            translation = self.translator.translate(text, dest='pt')
            self.last_translation = translation.text
            
            # Mostrar a tradução na nova janela
            translation_window = TranslationWindow(translation.text)
            translation_window.show()
            
            if hasattr(self, 'speech') and self.speech.voice_enabled:
                self.speech.speak(translation.text)
                
            return translation.text
        except Exception as e:
            logger.error(f"Error in translation: {str(e)}")
            raise
    
    def _validate_input(self, text):
        if not text or len(text) > 5000:
            return False
        suspicious_patterns = [
            '<script', 'javascript:', 'data:',
            'vbscript:', 'onload=', 'onerror='
        ]
        return not any(pattern in text.lower() for pattern in suspicious_patterns)

# Inicializar o tradutor
secure_translator = SecureTranslator()
def finalizar_programa():
    if 'resultado_janela' in globals() and resultado_janela:
        resultado_janela.destroy()
    tk_root.quit()

def criar_janela_resultado():
    global resultado_janela, label_resultado
    
    if resultado_janela is not None:
        return
        
    resultado_janela = tk.Toplevel(tk_root)
    resultado_janela.title("Tradução em Tempo Real")
    resultado_janela.geometry("600x300")
    resultado_janela.configure(bg="#1e1e1e" if tema_escuro else "#FFFFFF")
    resultado_janela.attributes('-topmost', True)
    
    # Centralizar a janela
    screen_width = resultado_janela.winfo_screenwidth()
    screen_height = resultado_janela.winfo_screenheight()
    window_width = 600
    window_height = 300
    position_top = (screen_height // 2) - (window_height // 2)
    position_left = (screen_width // 2) - (window_width // 2)
    resultado_janela.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')
    
    label_resultado = tk.Label(resultado_janela, text="", wraplength=580,
                             fg="white" if tema_escuro else "black",
                             bg="#1e1e1e" if tema_escuro else "#FFFFFF",
                             font=("Arial", 14, "bold"), padx=20, pady=20,
                             justify="center")
    label_resultado.pack(expand=True, fill="both")

def capturar_e_traduzir():
    try:
        tk_root.withdraw()
        time.sleep(0.5)
        
        x = tk_root.winfo_x()
        y = tk_root.winfo_y()
        w = tk_root.winfo_width()
        h = tk_root.winfo_height()
        
        imagem = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        tk_root.deiconify()
        
        texto_extraido = pytesseract.image_to_string(imagem, lang='eng').strip()
        
        if not texto_extraido:
            logger.warning("No text detected")
            return
        
        texto_traduzido = secure_translator.translate_and_speak(texto_extraido)
        
        if texto_traduzido:
            mostrar_resultado(texto_traduzido)
            
    except Exception as e:
        logger.error(f"Error in capture_and_translate: {str(e)}")
        messagebox.showerror("Erro", f"Erro durante a tradução: {str(e)}")

def mostrar_resultado(texto_traduzido):
    global resultado_janela, label_resultado
    
    if resultado_janela is None:
        criar_janela_resultado()
    
    label_resultado.config(text=texto_traduzido)
    
    if fechar_automaticamente:
        resultado_janela.after(int(tempo_fechamento * 1000), 
                             lambda: resultado_janela.destroy())

def iniciar_traducao_tempo_real():
    global traducao_em_tempo_real
    traducao_em_tempo_real = True
    criar_janela_resultado()
    
    thread_traducao = threading.Thread(target=atualizar_traducao, daemon=True)
    thread_traducao.start()
    
    botao_traduzir.configure(text="Parar Tradução", 
                            command=parar_traducao_tempo_real)

def parar_traducao_tempo_real():
    global traducao_em_tempo_real, resultado_janela, label_resultado
    traducao_em_tempo_real = False
    
    if resultado_janela:
        resultado_janela.destroy()
        resultado_janela = None
        label_resultado = None
    
    botao_traduzir.configure(text="Traduzir", 
                            command=alternar_modo_traducao)

def alternar_modo_traducao():
    if not traducao_em_tempo_real:
        iniciar_traducao_tempo_real()
    else:
        parar_traducao_tempo_real()

def atualizar_traducao():
    while traducao_em_tempo_real:
        capturar_e_traduzir()
        time.sleep(intervalo_atualizacao)

def abrir_menu(event):
    global menu_aberto
    if menu_aberto:
        menu_opcoes.unpost()
        menu_aberto = False
    else:
        menu_opcoes.post(event.x_root, event.y_root)
        menu_aberto = True

def load_config():
    global fechar_automaticamente, tempo_fechamento, tema_escuro, intervalo_atualizacao
    
    default_config = {
        'fechar_automaticamente': 'True',
        'tempo_fechamento': '10',
        'tema_escuro': 'True',
        'intervalo_atualizacao': '1.0',
        'voice_enabled': 'True'
    }
    
    try:
        if os.path.exists('config.encrypted'):
            with open('config.encrypted', 'r') as f:
                encrypted_data = f.read()
                config_data = json.loads(secure_translator.security.decrypt_data(encrypted_data))
        else:
            config_data = default_config
            
        fechar_automaticamente = config_data.get('fechar_automaticamente') == 'True'
        tempo_fechamento = int(config_data.get('tempo_fechamento', 10))
        tema_escuro = config_data.get('tema_escuro') == 'True'
        intervalo_atualizacao = float(config_data.get('intervalo_atualizacao', 1.0))
        secure_translator.speech.voice_enabled = config_data.get('voice_enabled') == 'True'
        
        if 'current_voice' in config_data:
            secure_translator.speech.set_voice(config_data['current_voice'])
    
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {str(e)}")
        return default_config

def atualizar_tema():
    cor_fundo = "black" if tema_escuro else "white"
    cor_texto = "white" if tema_escuro else "black"
    
    frame_borda.configure(bg=cor_fundo)
    botao_menu.configure(fg=cor_texto, bg=cor_fundo)
    menu_opcoes.configure(bg="#333333" if tema_escuro else "#FFFFFF",
                         fg=cor_texto)

# Funções de movimento da janela
def iniciar_mover(event):
    global movendo, pos_x, pos_y
    movendo = True
    pos_x = event.x_root - tk_root.winfo_x()
    pos_y = event.y_root - tk_root.winfo_y()

def mover_janela(event):
    if movendo:
        x = event.x_root - pos_x
        y = event.y_root - pos_y
        tk_root.geometry(f"+{x}+{y}")

def parar_mover(event):
    global movendo
    movendo = False

# Funções de redimensionamento
def iniciar_redimensionamento(event):
    global redimensionando
    redimensionando = True

def redimensionar_janela(event):
    if redimensionando:
        nova_largura = max(100, event.x_root - tk_root.winfo_x())
        nova_altura = max(50, event.y_root - tk_root.winfo_y())
        tk_root.geometry(f"{nova_largura}x{nova_altura}")

def parar_redimensionamento(event):
    global redimensionando
    redimensionando = False
def abrir_configuracoes():
    config_janela = tk.Toplevel(tk_root)
    config_janela.title("Configurações")
    config_janela.geometry("400x500")
    config_janela.attributes('-topmost', True)
    
    # Variáveis
    fechar_automaticamente_var = tk.BooleanVar(value=fechar_automaticamente)
    tempo_fechamento_var = tk.StringVar(value=str(tempo_fechamento))
    tema_var = tk.BooleanVar(value=tema_escuro)
    intervalo_var = tk.StringVar(value=str(intervalo_atualizacao))
    narracao_var = tk.BooleanVar(value=secure_translator.speech.voice_enabled)
    
    # Frame de configurações
    frame_config = ttk.Frame(config_janela, padding="10")
    frame_config.pack(fill="both", expand=True)
    
    # Opções gerais
    ttk.Label(frame_config, text="Configurações Gerais", 
              font=("Arial", 12, "bold")).pack(pady=10)
    
    ttk.Checkbutton(frame_config, text="Fechar tradução automaticamente",
                    variable=fechar_automaticamente_var).pack(pady=5)
    
    ttk.Label(frame_config, text="Tempo para fechar (segundos):").pack()
    ttk.Entry(frame_config, textvariable=tempo_fechamento_var).pack(pady=5)
    
    ttk.Checkbutton(frame_config, text="Tema escuro",
                    variable=tema_var).pack(pady=5)
    
    ttk.Label(frame_config, text="Intervalo de atualização (segundos):").pack()
    ttk.Entry(frame_config, textvariable=intervalo_var).pack(pady=5)
    
    # Configurações de voz
    ttk.Label(frame_config, text="Configurações de Voz", 
              font=("Arial", 12, "bold")).pack(pady=10)
    
    ttk.Checkbutton(frame_config, text="Ativar narração",
                    variable=narracao_var).pack(pady=5)
    
    # Seletor de voz
    ttk.Label(frame_config, text="Selecionar voz:").pack()
    voice_selector = ttk.Combobox(frame_config,
                                 values=list(secure_translator.speech.available_voices.keys()),
                                 state="readonly")
    voice_selector.pack(pady=5)
    voice_selector.set(secure_translator.speech.current_voice)
    voice_selector.bind('<<ComboboxSelected>>',
                       lambda e: secure_translator.speech.set_voice(voice_selector.get()))
    
    def salvar_configuracoes():
        global fechar_automaticamente, tempo_fechamento, tema_escuro, intervalo_atualizacao
        
        try:
            fechar_automaticamente = fechar_automaticamente_var.get()
            tempo_fechamento = int(tempo_fechamento_var.get())
            tema_escuro = tema_var.get()
            novo_intervalo = float(intervalo_var.get())
            
            if novo_intervalo <= 0:
                raise ValueError("Intervalo deve ser maior que zero")
            
            intervalo_atualizacao = novo_intervalo
            secure_translator.speech.voice_enabled = narracao_var.get()
            
            config = {
                'fechar_automaticamente': str(fechar_automaticamente),
                'tempo_fechamento': str(tempo_fechamento),
                'tema_escuro': str(tema_escuro),
                'intervalo_atualizacao': str(intervalo_atualizacao),
                'voice_enabled': str(secure_translator.speech.voice_enabled),
                'current_voice': secure_translator.speech.current_voice
            }
            
            encrypted_config = secure_translator.security.encrypt_data(json.dumps(config))
            with open('config.encrypted', 'w') as f:
                f.write(encrypted_config)
            
            logger.info("Configurações salvas com sucesso")
            atualizar_tema()
            config_janela.destroy()
            
        except ValueError as e:
            logger.error(f"Erro ao salvar configurações: {str(e)}")
            messagebox.showerror("Erro", "Valores inválidos nas configurações!")
    
    # Botões de ação
    frame_botoes = ttk.Frame(frame_config)
    frame_botoes.pack(pady=20)
    
    ttk.Button(frame_botoes, text="Salvar", 
               command=salvar_configuracoes).pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_botoes, text="Cancelar", 
               command=config_janela.destroy).pack(side=tk.LEFT, padx=5)

# Inicialização da interface principal
tk_root = tk.Tk()
tk_root.title("Tradutor de Tela")
tk_root.geometry("300x150")
tk_root.attributes('-topmost', True)
tk_root.attributes('-alpha', 0.3)
tk_root.overrideredirect(True)

# Frame principal
frame_borda = tk.Frame(tk_root, bd=2, relief="solid", 
                      bg="black" if tema_escuro else "white")
frame_borda.pack(expand=True, fill="both", padx=2, pady=2)

# Menu
menu_opcoes = tk.Menu(tk_root, tearoff=0)
menu_opcoes.add_command(label="Configurações", 
                       command=lambda: abrir_configuracoes())
menu_opcoes.add_command(label="Sair", command=finalizar_programa)

# Botão de menu
botao_menu = tk.Label(frame_borda, text="⋮", 
                     fg="white" if tema_escuro else "black",
                     bg="black" if tema_escuro else "white",
                     font=("Arial", 12))
botao_menu.place(relx=0.95, rely=0.05, anchor="ne")
botao_menu.bind("<Button-1>", abrir_menu)

# Botão de tradução
botao_traduzir = ttk.Button(frame_borda, text="Traduzir",
                           command=alternar_modo_traducao)
botao_traduzir.pack(pady=10)

# Bindings para movimento e redimensionamento
frame_borda.bind('<ButtonPress-1>', iniciar_mover)
frame_borda.bind('<B1-Motion>', mover_janela)
frame_borda.bind('<ButtonRelease-1>', parar_mover)

# Área de redimensionamento
resizer = tk.Frame(frame_borda, width=10, height=10, 
                  bg="gray", cursor="bottom_right_corner")
resizer.place(relx=1.0, rely=1.0, anchor="se")

resizer.bind('<ButtonPress-1>', iniciar_redimensionamento)
resizer.bind('<B1-Motion>', redimensionar_janela)
resizer.bind('<ButtonRelease-1>', parar_redimensionamento)

# Atalhos de teclado
tk_root.bind('<Control-t>', lambda e: alternar_modo_traducao())
tk_root.bind('<Escape>', lambda e: parar_traducao_tempo_real())

# Protocolo de fechamento
tk_root.protocol("WM_DELETE_WINDOW", finalizar_programa)

if __name__ == "__main__":
    try:
        # Verificar dependências
        check_dependencies()
        
        # Configurar logging
        setup_logging()
        logger.info("Iniciando aplicação...")
        
        # Carregar configurações
        load_config()
        
        # Atualizar tema
        atualizar_tema()
        
        # Iniciar interface
        tk_root.deiconify()
        
        logger.info("Aplicação iniciada com sucesso")
        tk_root.mainloop()
        
    except Exception as e:
        logger.critical(f"Erro crítico na aplicação: {str(e)}")
        messagebox.showerror("Erro Crítico", 
                           "Ocorreu um erro crítico na aplicação. Verifique os logs para mais detalhes.")
        exit(1)