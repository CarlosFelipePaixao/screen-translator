import tkinter as tk
from tkinter import ttk, messagebox
import pytesseract
from googletrans import Translator
from PIL import ImageGrab
import time
import configparser

# Configuração do Tesseract (precisa estar instalado no sistema)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Variáveis globais
fechar_automaticamente = False
tempo_fechamento = 10  # Tempo padrão de 10 segundos
menu_aberto = False  # Definição da variável global menu_aberto
tema_escuro = True  # Definir tema escuro como padrão

# Carregar configurações
config = configparser.ConfigParser()
config.read('config.ini')

# Função para capturar a tela atrás da janela e traduzir
def capturar_e_traduzir():
    # Pequeno atraso para evitar capturar a própria janela
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
        messagebox.showwarning("Aviso", "Nenhum texto detectado na área selecionada!")
        return
    
    translator = Translator()
    texto_traduzido = translator.translate(texto_extraido, src='en', dest='pt').text
    
    # Criar uma nova janela para exibir o resultado de forma estilizada
    resultado_janela = tk.Toplevel(tk_root)
    resultado_janela.title("Tradução")
    resultado_janela.geometry("600x300")  # Tornar a janela mais retangular
    resultado_janela.configure(bg="#1e1e1e" if tema_escuro else "#FFFFFF")  # Cor de fundo baseada no tema
    resultado_janela.attributes('-topmost', True)
    
    # Centralizando a janela de tradução
    screen_width = resultado_janela.winfo_screenwidth()
    screen_height = resultado_janela.winfo_screenheight()
    window_width = 600
    window_height = 300
    position_top = (screen_height // 2) - (window_height // 2)
    position_left = (screen_width // 2) - (window_width // 2)

    # Posicionar a janela de tradução no centro da tela
    resultado_janela.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')
    
    label_resultado = tk.Label(resultado_janela, text=texto_traduzido, wraplength=580, 
                               fg="white" if tema_escuro else "black", bg="#1e1e1e" if tema_escuro else "#FFFFFF",
                               font=("Arial", 14, "bold"), padx=20, pady=20, justify="center")
    label_resultado.pack(expand=True, fill="both")
    
    # Fechar automaticamente, se a opção estiver marcada
    if fechar_automaticamente:
        tempo_fechamento_ms = int(tempo_fechamento) * 1000  # Converter para milissegundos
        resultado_janela.after(tempo_fechamento_ms, resultado_janela.destroy)
    
    # Fechar a janela ao clicar em qualquer lugar ou pressionar uma tecla
    resultado_janela.bind("<Button-1>", lambda e: resultado_janela.destroy())
    resultado_janela.bind("<KeyPress>", lambda e: resultado_janela.destroy())

# Função para abrir a janela de configurações
def abrir_configuracoes():
    # Criar a janela de configurações
    config_janela = tk.Toplevel(tk_root)
    config_janela.title("Configurações")
    config_janela.geometry("400x300")
    
    # Variáveis de configurações
    fechar_automaticamente_var = tk.BooleanVar(value=fechar_automaticamente)
    tempo_fechamento_var = tk.StringVar(value=str(tempo_fechamento))
    tema_var = tk.BooleanVar(value=tema_escuro)
    
    # Opção de "Fechar tradução automaticamente"
    fechar_checkbutton = tk.Checkbutton(config_janela, text="Fechar tradução automaticamente", 
                                        variable=fechar_automaticamente_var)
    fechar_checkbutton.pack(pady=10)
    
    # Campo para inserir o tempo em segundos
    tempo_label = tk.Label(config_janela, text="Tempo (em segundos) para fechar:")
    tempo_label.pack()
    tempo_entry = tk.Entry(config_janela, textvariable=tempo_fechamento_var)
    tempo_entry.pack(pady=10)

    # Opção para tema claro/escuro
    tema_checkbutton = tk.Checkbutton(config_janela, text="Usar tema escuro", 
                                      variable=tema_var)
    tema_checkbutton.pack(pady=10)
    
    # Botão de salvar as configurações
    def salvar_configuracoes():
        global fechar_automaticamente, tempo_fechamento, tema_escuro
        fechar_automaticamente = fechar_automaticamente_var.get()
        tempo_fechamento = tempo_fechamento_var.get()
        tema_escuro = tema_var.get()
        
        # Salvar as configurações no arquivo
        config['Config'] = {
            'fechar_automaticamente': str(fechar_automaticamente),
            'tempo_fechamento': str(tempo_fechamento),
            'tema_escuro': str(tema_escuro)
        }
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        
        config_janela.destroy()
    
    salvar_button = ttk.Button(config_janela, text="Salvar", command=salvar_configuracoes)
    salvar_button.pack(pady=10)
    
    # Botão de sair
    sair_button = ttk.Button(config_janela, text="Sair", command=config_janela.destroy)
    sair_button.pack(pady=5)

# Criar a interface
tk_root = tk.Tk()
tk_root.title("Tradutor de Tela")
tk_root.geometry("300x150")
tk_root.attributes('-topmost', True)  # Manter sempre no topo
tk_root.attributes('-alpha', 0.3)  # Tornar a janela transparente

tk_root.overrideredirect(True)  # Remover bordas padrão

# Funções para mover e redimensionar
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

def iniciar_redimensionamento(event):
    global redimensionando
    redimensionando = True
    pos_x = event.x_root
    pos_y = event.y_root

def redimensionar_janela(event):
    if redimensionando:
        nova_largura = max(100, event.x_root - tk_root.winfo_x())
        nova_altura = max(50, event.y_root - tk_root.winfo_y())
        tk_root.geometry(f"{nova_largura}x{nova_altura}")

def parar_redimensionamento(event):
    global redimensionando
    redimensionando = False

# Criar menu suspenso
def abrir_menu(event):
    global menu_aberto
    if menu_aberto:
        menu_opcoes.unpost()
        menu_aberto = False
    else:
        menu_opcoes.post(event.x_root, event.y_root)
        menu_aberto = True

# Criar moldura para borda
frame_borda = tk.Frame(tk_root, bd=2, relief="solid", bg="black" if tema_escuro else "white")
frame_borda.pack(expand=True, fill="both", padx=2, pady=2)
frame_borda.bind('<ButtonPress-1>', iniciar_mover)
frame_borda.bind('<B1-Motion>', mover_janela)
frame_borda.bind('<ButtonRelease-1>', parar_mover)

# Criar botão discreto para menu
botao_menu = tk.Label(frame_borda, text="⋮", fg="white" if tema_escuro else "black", bg="black" if tema_escuro else "white", font=("Arial", 12))
botao_menu.place(relx=0.95, rely=0.05, anchor="ne")
botao_menu.bind("<Button-1>", abrir_menu)

# Criar menu de opções
menu_opcoes = tk.Menu(tk_root, tearoff=0, bg="#333333" if tema_escuro else "#FFFFFF", fg="white" if tema_escuro else "black", font=("Arial", 10))
menu_opcoes.add_command(label="Configurações", command=abrir_configuracoes)
menu_opcoes.add_command(label="Sair", command=tk_root.quit)

# Área de canto inferior direito para redimensionar
resizer = tk.Frame(frame_borda, width=10, height=10, bg="gray", cursor="bottom_right_corner")
resizer.place(relx=1.0, rely=1.0, anchor="se")
resizer.bind('<ButtonPress-1>', iniciar_redimensionamento)
resizer.bind('<B1-Motion>', redimensionar_janela)
resizer.bind('<ButtonRelease-1>', parar_redimensionamento)

# Botão para traduzir
botao_traduzir = ttk.Button(frame_borda, text="Traduzir", command=capturar_e_traduzir)
botao_traduzir.pack(pady=10)

# Iniciar aplicação
tk_root.mainloop()
