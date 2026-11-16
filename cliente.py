from tkinter import messagebox
import xmlrpc.client
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
from estilo import BOTAO_AMARELO, BOTAO_ESCURO, COR_AMARELO, COR_AZUL, FONTE_PADRAO, HOVER_AMARELO

proxy = xmlrpc.client.ServerProxy("http://localhost:9876") # conexão com o servidor XML-RPC

# janela principal do cliente
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("O Pequeno Contexto")
        self.geometry("900x600") # fixa o tamanho da janela
        self.resizable(False, False)

        self.tela_atual = self.tela_anterior = None
        self.container = ctk.CTkFrame(self, fg_color=COR_AZUL)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for Tela in (TelaMenu, TelaAjuda, TelaSobre, TelaJogo, TelaResultado):
            frame = Tela(self.container, self)
            self.frames[Tela] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.mostrar_tela(TelaMenu) # exibe a tela inicial do menu

    # função para alternar entre as telas do programa
    def mostrar_tela(self, tela_classe):
        if self.tela_atual == TelaMenu and tela_classe == TelaJogo:
            self.frames[TelaJogo].resetar_tela() 

        if self.tela_atual and self.tela_atual != tela_classe:
            self.tela_anterior = self.tela_atual
        self.tela_atual = tela_classe
        self.frames[tela_classe].tkraise()

    # função para voltar pra tela anterior ou pro menu principal
    def voltar_tela(self):
        self.mostrar_tela(self.tela_anterior or TelaMenu)

# tela base que todas as outras telas herdam com fundo e título
class TelaBase(ctk.CTkFrame):
    def __init__(self, container, app, texto_titulo, tamanho_fonte=90, pos_y=25):
        super().__init__(container, fg_color=COR_AZUL)
        self.app = app

        img = Image.open("recursos/fundo.png").convert("RGB") # abre a imagem de fundo
        desenho = ImageDraw.Draw(img)
        try:
            fonte = ImageFont.truetype("recursos/fonte.ttf", tamanho_fonte) # tenta carregar a fonte personalizada
        except OSError:
            fonte = ImageFont.load_default()

        pos_x = 450
        desenho.multiline_text((pos_x + 3, pos_y + 3), texto_titulo, font=fonte, fill=COR_AZUL, anchor="ma", align="center", spacing=10)
        desenho.multiline_text((pos_x, pos_y), texto_titulo, font=fonte, fill=COR_AMARELO, anchor="ma", align="center", spacing=10)

        self.ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(900, 600))
        ctk.CTkLabel(self, image=self.ctk_img, text="").place(relx=0.5, rely=0.5, anchor="center")

    #função para criar uma caixinha com texto centralizado
    def criar_caixa_conteudo(self, texto):
        caixa = ctk.CTkFrame(self, fg_color=COR_AMARELO, border_width=2, border_color=COR_AZUL, corner_radius=0, width=720, height=300)
        caixa.place(relx=0.5, rely=0.53, anchor="center")
        caixa.pack_propagate(False)
        ctk.CTkLabel(caixa, text=texto, font=(FONTE_PADRAO, 18), text_color=COR_AZUL, justify="center").pack(expand=True, fill="both", padx=20, pady=15)

    def criar_botao_voltar(self):
        ctk.CTkButton(self, text="Voltar", width=280, height=55, command=self.app.voltar_tela, **BOTAO_AMARELO).place(relx=0.5, rely=0.88, anchor="center")

# confirmação pra sair pro menu no meio da partida:
class ConfirmaSair(ctk.CTkToplevel):
    def __init__(self, app, titulo, mensagem):
        super().__init__(app, fg_color=COR_AZUL)
        self.title(titulo)
        self.resizable(False, False)
        self.resultado = False # só vira true se o jogador clicar em Sim

        largura, altura = 440, 210
        x = app.winfo_x() + (app.winfo_width() - largura) // 2 # centraliza o pop-up sobre a janela principal
        y = app.winfo_y() + (app.winfo_height() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.transient(app)

        caixa = ctk.CTkFrame(self, fg_color=COR_AMARELO, border_width=2, border_color=COR_AZUL, corner_radius=0)
        caixa.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(caixa, text=mensagem, font=(FONTE_PADRAO, 16), text_color=COR_AZUL, justify="center", wraplength=380).pack(expand=True, padx=15, pady=(15, 5))

        botoes = ctk.CTkFrame(caixa, fg_color="transparent")
        botoes.pack(pady=(5, 15))
        ctk.CTkButton(botoes, text="Sim", width=120, command=lambda: self._responder(True), **BOTAO_ESCURO).pack(side="left", padx=10)
        ctk.CTkButton(botoes, text="Não", width=120, command=lambda: self._responder(False), **BOTAO_ESCURO).pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", lambda: self._responder(False)) # fechar no X conta como "Não"
        self.bind("<Escape>", lambda e: self._responder(False))
        self.after(50, self._prender) # espera a janela aparecer antes de prender o foco nela

    def _prender(self):
        self.grab_set() # bloqueia a janela principal enquanto o pop-up estiver aberto
        self.focus()

    def _responder(self, valor):
        self.resultado = valor
        self.destroy()

# telas do programa
class TelaMenu(TelaBase):
    def __init__(self, container, app):
        super().__init__(container, app, "O Pequeno\nContexto", 88, 25)
        botoes = [
            ("Iniciar Jogo", lambda: app.mostrar_tela(TelaJogo)),
            ("Ajuda", lambda: app.mostrar_tela(TelaAjuda)),
            ("Sobre", lambda: app.mostrar_tela(TelaSobre)),
            ("Sair", app.destroy)
        ]
        for i, (texto, cmd) in enumerate(botoes):
            ctk.CTkButton(self, text=texto, command=cmd, width=280, height=55, **BOTAO_AMARELO).place(relx=0.5, rely=0.51 + i * 0.12, anchor="center")

# tela do jogo
class TelaJogo(TelaBase):
    def __init__(self, container, app):
        super().__init__(container, app, "O Pequeno Contexto", 46, 10)
        self.jogo_ativo = True
        self.historico_local = []
        self.ocupado = False # trava de requisição, true enquanto o servidor ainda não respondeu
        self.botoes = []

        # topo da tela com botões e tentativas
        topo = ctk.CTkFrame(self, fg_color=COR_AMARELO, border_width=2, border_color=COR_AZUL, corner_radius=0, height=50)
        topo.place(relx=0.5, rely=0.15, anchor="center", relwidth=0.8)
        topo.pack_propagate(False)

        btn_menu = ctk.CTkButton(topo, text="Menu", width=80, command=self.sair_para_menu, **BOTAO_ESCURO)
        btn_menu.pack(side="left", padx=(8, 4), pady=8)
        btn_ajuda = ctk.CTkButton(topo, text="Ajuda", width=80, command=lambda: app.mostrar_tela(TelaAjuda), **BOTAO_ESCURO)
        btn_ajuda.pack(side="left", padx=4, pady=8)
        
        self.label_tentativas = ctk.CTkLabel(topo, text="TENTATIVAS: 0", font=(FONTE_PADRAO, 15, "bold"), text_color=COR_AZUL)
        self.label_tentativas.pack(side="left", expand=True)
        
        btn_desistir = ctk.CTkButton(topo, text="Desistir", width=90, command=self.desistir, **BOTAO_ESCURO)
        btn_desistir.pack(side="right", padx=(4, 8), pady=8)
        btn_dica = ctk.CTkButton(topo, text="Dica", width=80, command=self.pedir_dica, **BOTAO_ESCURO)
        btn_dica.pack(side="right", padx=4, pady=8)

        # entrada de palavra e botão de envio
        inp_frame = ctk.CTkFrame(self, fg_color="transparent")
        inp_frame.place(relx=0.5, rely=0.25, anchor="center", relwidth=0.8)

        self.entrada = ctk.CTkEntry(
            inp_frame,
            placeholder_text="Digite uma palavra...",
            font=(FONTE_PADRAO, 16),
            height=45,
            fg_color=COR_AZUL,
            bg_color="transparent",
            text_color="white",
            border_width=2,
            border_color=COR_AMARELO,
            corner_radius=0
        )
        self.entrada.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entrada.bind("<Return>", self.enviar_palpite)

        btn_enviar = ctk.CTkButton(inp_frame, text="Enviar", width=110, height=45, command=self.enviar_palpite, **BOTAO_AMARELO)
        btn_enviar.pack(side="right")

        self.botoes = [btn_menu, btn_ajuda, btn_desistir, btn_dica, btn_enviar]

        # área de histórico de tentativas
        self.historico = ctk.CTkScrollableFrame(self, width=700, height=340, fg_color=COR_AZUL, border_width=2, border_color=COR_AMARELO, corner_radius=0, scrollbar_button_color=COR_AMARELO, scrollbar_button_hover_color=HOVER_AMARELO)
        self.historico.place(relx=0.5, rely=0.63, anchor="center")

    # função que volta pro menu e pede confirmação se ainda tem partida em andamento
    def sair_para_menu(self):
        if self.ocupado:
            return
        if self.jogo_ativo:
            popup = ConfirmaSair(self.app, "Voltar ao menu", "Deseja mesmo voltar ao menu?\nSua partida atual será perdida.")
            self.wait_window(popup) # espera o jogador responder
            if not popup.resultado:
                return
        self.app.mostrar_tela(TelaMenu)

    # habilita/desabilita todos os botões da tela de jogo
    def _travar_botoes(self, travar):
        estado = "disabled" if travar else "normal"
        for botao in self.botoes:
            botao.configure(state=estado)

    # função que só deixa passar uma requisição por vez:
    def _chamar(self, funcao, *args):
        if self.ocupado:
            return None
        self.ocupado = True
        self._travar_botoes(True)
        self.update_idletasks() # redesenha os botões já desabilitados antes de bloquear na chamada
        try:
            return funcao(*args)
        except (OSError, xmlrpc.client.Error):
            messagebox.showerror("Erro", "Não foi possível conectar ao servidor.\nVerifique se o servidor.py está rodando.")
            return None
        finally:
            # a janela fica congelada durante a chamada
            self.update()
            self._travar_botoes(False)
            self.ocupado = False

    # função para resetar a tela do jogo e iniciar uma nova partida
    def resetar_tela(self):
        if self.ocupado:
            return
        self.jogo_ativo = True
        self.historico_local = []
        self.label_tentativas.configure(text="TENTATIVAS: 0")
        self.entrada.delete(0, "end")
        for item in self.historico.winfo_children(): # limpa o histórico de tentativas da tela
            item.destroy()

        if self._chamar(proxy.iniciar_partida) is None: # sem conexão com o servidor
            self.jogo_ativo = False

    # função para enviar o palpite do jogador ao servidor e processar a resposta
    def enviar_palpite(self, event=None):
        palavra = self.entrada.get().strip()
        if not palavra or not self.jogo_ativo or self.ocupado:
            return

        resultado = self._chamar(proxy.tentar_palavra, palavra)
        if resultado is None: # sem conexão com o servidor
            return

        if "erro" in resultado:
            messagebox.showwarning("Aviso", resultado["erro"])
            return

        self.entrada.delete(0, "end")
        self.label_tentativas.configure(text=f"TENTATIVAS: {resultado['total_tentativas']}")
        
        self.atualizar_historico_servidor(resultado["historico"], resultado["total"]) # atualiza o histórico de tentativas na tela do cliente

        if resultado["venceu"]: # se o jogador venceu exibe a tela de resultado com a palavra secreta e estatísticas
            self.jogo_ativo = False
            self.app.frames[TelaResultado].mostrar_resultado(
                venceu=True,
                palavra_secreta=resultado["palavra"],
                tentativas=resultado["total_tentativas"],
                dicas_usadas=resultado["total_dicas"],
            )
            self.app.mostrar_tela(TelaResultado)

    def pedir_dica(self):
        if not self.jogo_ativo or self.ocupado:
            return

        resultado = self._chamar(proxy.pedir_dica)
        if resultado is None:
            return

        if "erro" in resultado:
            messagebox.showinfo("Dica", resultado["erro"])
            return

        self.atualizar_historico_servidor(resultado["historico"], resultado["total"])

    def desistir(self):
        if not self.jogo_ativo or self.ocupado:
            return

        resultado = self._chamar(proxy.desistir_partida)
        if resultado is None:
            return
        if "erro" in resultado: # nenhuma partida ativa
            messagebox.showinfo("Desistir", resultado["erro"])
            return

        self.jogo_ativo = False
        self.app.frames[TelaResultado].mostrar_resultado(
            venceu=False,
            palavra_secreta=resultado["palavra_secreta"],
            tentativas=resultado["total_tentativas"],
            dicas_usadas=resultado["total_dicas"],
            mais_proximas=resultado.get("mais_proximas"),
        )
        self.app.mostrar_tela(TelaResultado)

    def atualizar_historico_servidor(self, historico_servidor, total_vocabulario):
        self.historico_local = historico_servidor
        
        historico_ordenado = sorted(historico_servidor, key=lambda x: x["posicao"]) # ordena o histórico de tentativas pelo ranking de proximidade

        for item in self.historico.winfo_children():
            item.destroy()

        for entrada in historico_ordenado:
            cor = self._cor_por_posicao(entrada["posicao"], total_vocabulario)
            self._desenhar_card(entrada["palavra"], entrada["posicao"], cor, entrada.get("eh_dica", False))

    def _cor_por_posicao(self, posicao, total):
        if posicao <= max(1, total * 0.02):
            return "#2ecc71"  # verde se estiver próximo 
        if posicao <= max(1, total * 0.20):
            return "#f1c40f"  # amarelo se estiver razoavelmente próximo
        return "#e63946"  # vermelho se estiver distante

    def _desenhar_card(self, palavra, posicao, cor, eh_dica=False):
        card = ctk.CTkFrame(self.historico, fg_color="#121b40", border_width=1, border_color=COR_AMARELO, corner_radius=0, height=42)
        card.pack(fill="x", pady=4, padx=5)
        card.pack_propagate(False)

        texto_palavra = f"{palavra}  💡" if eh_dica else palavra

        ctk.CTkFrame(card, fg_color=cor, width=12, corner_radius=0).pack(side="left", fill="y")
        ctk.CTkLabel(card, text=texto_palavra, font=(FONTE_PADRAO, 15, "bold"), text_color="white", anchor="w").pack(side="left", padx=15)
        ctk.CTkLabel(card, text=str(posicao), font=(FONTE_PADRAO, 15, "bold"), text_color=COR_AMARELO, anchor="e").pack(side="right", padx=15)

# tela de resultado do jogo
class TelaResultado(TelaBase):
    def __init__(self, container, app):
        super().__init__(container, app, "Fim de Jogo", 70, 20)
        self._caixa = ctk.CTkFrame(self, fg_color=COR_AMARELO, border_width=2, border_color=COR_AZUL, corner_radius=0, width=720, height=300)
        self._caixa.place(relx=0.5, rely=0.53, anchor="center")
        self._caixa.pack_propagate(False)
        self.label_resultado = ctk.CTkLabel(self._caixa, text="", font=(FONTE_PADRAO, 18), text_color=COR_AZUL, justify="center")
        self.label_resultado.pack(expand=True, fill="both", padx=20, pady=15)

        ctk.CTkButton(self, text="Voltar ao Menu", width=280, height=55, command=lambda: app.mostrar_tela(TelaMenu), **BOTAO_AMARELO).place(relx=0.5, rely=0.88, anchor="center")

    def mostrar_resultado(self, venceu, palavra_secreta, tentativas, dicas_usadas, mais_proximas=None):
        if venceu: # se o jogador venceu exibe a tela de resultado com a palavra secreta e estatísticas
            titulo = "Parabéns! Você venceu!"
            texto = (
                f"{titulo}\n\n"
                f"A palavra secreta era: {palavra_secreta.upper()}\n\n"
                f"Tentativas: {tentativas}   |   Dicas usadas: {dicas_usadas}"
            )
        else: # se o jogador desistiu exibe a tela de resultado com a palavra secreta e estatísticas
            titulo = "Mais sorte na próxima!"
            texto = (
                f"{titulo}\n\n"
                f"A palavra secreta era: {palavra_secreta.upper()}\n\n"
                f"Tentativas: {tentativas}   |   Dicas usadas: {dicas_usadas}"
            )
            if mais_proximas:
                texto += "\n\nPalavras próximas: " + ", ".join(mais_proximas)

        self.label_resultado.configure(text=texto)

# telas de ajuda sobre como jogar 
class TelaAjuda(TelaBase):
    def __init__(self, container, app):
        super().__init__(container, app, "Como Jogar", 90, 25)
        txt = ("Descubra a palavra secreta escondida no livro O Pequeno Príncipe!\n\n"
               "A cada tentativa, você digita uma palavra e o jogo mostra a posição\n"
               "dela em um ranking de proximidade semântica com a resposta certa.\n\n"
               "Quanto mais próxima a posição de 1, mais perto você está da palavra secreta.\n\n"
               "Use o botão de Dica se estiver travado, e Desistir caso queira ver a resposta.\n\n"
               "Não há limite de tentativas nem de tempo!")
        self.criar_caixa_conteudo(txt)
        self.criar_botao_voltar()

# tela de informações sobre os alunos e o trabalho
class TelaSobre(TelaBase):
    def __init__(self, container, app):
        super().__init__(container, app, "Sobre", 90, 25)
        txt = ("Desenvolvido por:\n"
               "Christiano, Mizael e Maria Luiza\n\n"
               "Trabalho apresentado às disciplinas de\n"
               "Inteligência Artificial e Redes de Computadores e Sistemas Distribuídos\n\n"
               "Curso de Bacharelado em Ciência da Computação\n"
               "Universidade Estadual do Paraná - UNESPAR")
        self.criar_caixa_conteudo(txt)
        self.criar_botao_voltar()


if __name__ == "__main__":
    App().mainloop()