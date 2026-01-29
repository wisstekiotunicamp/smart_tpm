import io
import re
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import markdown2
from bs4 import BeautifulSoup
from pypdf import PdfWriter, PdfReader
from PIL import Image

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dark_blue_rgb = (41, 128, 185)
        # Título padrão caso não seja definido externamente
        self.doc_title = 'Relatório Smart TpM'

    def header(self):
        self.set_font('Helvetica', 'B', 15)
        # Usa o título dinâmico definido na função de geração
        self.cell(0, 10, self.doc_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

    def add_section_title(self, title, color):
        r, g, b = color
        self.set_text_color(r, g, b)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_draw_color(r, g, b)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def add_markdown_body(self, markdown_text, color):
        r, g, b = color
        # Converte Markdown para HTML para processar tags básicas
        html = markdown2.markdown(markdown_text, extras=["cuddled-lists"])
        soup = BeautifulSoup(html, "html.parser")
        
        original_l_margin = self.l_margin
        content_width = self.w - self.l_margin - self.r_margin - 10
        self.set_left_margin(original_l_margin + 5)
        
        start_y = self.get_y()
        # Verifica se cabe na página, senão quebra
        if start_y > 250: 
            self.add_page()
            start_y = self.get_y()

        box_x = original_l_margin
        box_start_y = start_y
        self.set_draw_color(r, g, b)
        self.set_line_width(0.3)

        def render_formatted_line(line_text, is_list_item=False, indent=0):
            self.set_text_color(0, 0, 0)
            if is_list_item:
                bullet_x = self.get_x() + (indent * 5)
                self.set_x(bullet_x)
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(r, g, b)
                self.cell(5, 6, "-")
                self.set_x(bullet_x + 5)
                self.set_text_color(0, 0, 0)
            else:
                self.set_x(self.get_x() + (indent * 5))
            
            # Tratamento simples de negrito e itálico (regex básico)
            line_text = line_text.replace("\n", " ").strip()
            line_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line_text)
            line_text = re.sub(r"_(.*?)_", r"<i>\1</i>", line_text)
            
            # Simulação de write_html (ou uso direto se FPDF suportar na versão instalada)
            # Aqui usamos uma lógica manual para garantir compatibilidade básica
            parts = re.split(r"(<b>|</b>|<i>|</i>)", line_text)
            style = ""
            for part in parts:
                if part == "<b>": style = "B"
                elif part == "</b>": style = ""
                elif part == "<i>": style = "I"
                elif part == "</i>": style = ""
                elif part:
                    self.set_font("Helvetica", style, 10)
                    self.write(6, part)
            self.ln(6)

        for elem in soup.children:
            if elem.name is None: continue
            text = elem.get_text(" ", strip=True)
            if not text: continue
            
            if elem.name == "h1":
                self.set_font("Helvetica", "B", 12)
                self.set_text_color(r, g, b)
                self.multi_cell(content_width, 8, text)
                self.ln(2)
            elif elem.name == "h2":
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(r, g, b)
                self.multi_cell(content_width, 7, text)
                self.ln(2)
            elif elem.name == "h3":
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(r, g, b)
                self.multi_cell(content_width, 7, text)
                self.ln(2)
            elif elem.name == "p":
                render_formatted_line(elem.get_text(" ", strip=True), is_list_item=False)
                self.ln(2)
            elif elem.name in ["ul", "ol"]:
                list_items = elem.find_all("li")
                if not list_items: continue
                for item in list_items:
                    item_text = item.get_text(" ", strip=True)
                    render_formatted_line(item_text, is_list_item=True)
                self.ln(2)

        y_after = self.get_y()
        box_height = y_after - box_start_y
        if box_height < 5: box_height = 10
        
        # Retorna margem e desenha caixa
        self.set_left_margin(original_l_margin)
        self.rect(box_x, box_start_y, content_width + 5, box_height)
        self.set_y(y_after + 5)
        self.set_text_color(0, 0, 0)

def formatar_texto_usuario(texto_bruto):
    if not texto_bruto: return "Nenhum dado fornecido."
    # Garante espaçamento em Markdown
    texto = re.sub(r'(##)(?=[^\s])', r'\1 ', texto_bruto)
    texto = re.sub(r'(\n|^)-([^\s])', r'\1- \2', texto)
    texto = re.sub(r'(?<!\n)\n(##)', r'\n\n\1', texto)
    return texto

def gerar_pdf_com_anexos(data, lista_anexos, tipo_relatorio='fase1'):
    print(f">>> PDF Generator: Iniciando para {tipo_relatorio}...")
    cor_destaque = (41, 128, 185)
    
    pdf = PDF()
    
    # 1. Configura Título do Documento com base na Fase
    if tipo_relatorio == 'fase1':
        pdf.doc_title = 'Relatório de Negócio - Fase 1 TpM'
    elif tipo_relatorio == 'fase2':
        pdf.doc_title = 'Relatório de Requisitos - Fase 2 TpM'
    elif tipo_relatorio == 'fase3':
        pdf.doc_title = 'Relatório de Implementação - Fase 3 TpM'
    else:
        pdf.doc_title = 'Relatório Smart TpM'

    pdf.add_page()

    # 2. Cabeçalho do Projeto (Comum a todas as fases)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(25, 7, 'Projeto:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, data.get('nome_projeto', 'Não informado'), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(28, 7, 'Responsável:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
    pdf.set_font('Helvetica', '', 11)
    # Recupera responsável (enviado pelo hidden input nas fases 2 e 3)
    pdf.cell(0, 7, data.get('responsavel', 'Não informado'), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(8)

    # 3. Definição dos Campos por Fase
    campos = []
    titulos = []

    if tipo_relatorio == 'fase1':
        # Fase 1: Negócio
        campos = ['contexto', 'negocio', 'regras', 'especialista', 'coisas']
        titulos = ['Contextualização', 'Negócio (Business)', 'Regras de Negócio', 'Especialista', 'Coisas (Things)']
        
    elif tipo_relatorio == 'fase2':
        # Fase 2: Requisitos (Top-Down)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 10, 'Abordagem Top-Down: Do Usuário para a Coisa', ln=True, align='L')
        pdf.ln(2)
        
        campos = ['l6_display', 'l5_abstraction', 'l4_storage', 'l3_border', 'l2_connectivity', 'l1_sensor']
        titulos = [
            'Nível 6 - Display (Visualização)', 
            'Nível 5 - Abstraction (Abstração)', 
            'Nível 4 - Storage (Armazenamento)', 
            'Nível 3 - Border (Borda)', 
            'Nível 2 - Connectivity (Conectividade)', 
            'Nível 1 - Sensor/Actuator (Sensores)'
        ]

    elif tipo_relatorio == 'fase3':
        # Fase 3: Implementação (Bottom-Up)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 10, 'Abordagem Bottom-Up: Do Hardware para a Interface', ln=True, align='L')
        pdf.ln(2)
        
        campos = ['impl_l1', 'impl_l2', 'impl_l3', 'impl_l4', 'impl_l5', 'impl_l6']
        titulos = [
            'Nível 1 - Sensor/Actuator (Hardware)', 
            'Nível 2 - Connectivity (Protocolos)', 
            'Nível 3 - Border (Gateway/Edge)', 
            'Nível 4 - Storage (Banco de Dados)', 
            'Nível 5 - Abstraction (Algoritmos)', 
            'Nível 6 - Display (Frontend/App)'
        ]

    # 4. Renderiza os Campos
    for c, t in zip(campos, titulos):
        pdf.add_section_title(t, cor_destaque)
        # data.get(c) busca o valor do campo no dicionário enviado pelo formulário
        pdf.add_markdown_body(formatar_texto_usuario(data.get(c)), cor_destaque)

    # 5. Gera o PDF Base em Memória
    base_pdf_bytes = pdf.output()
    pdf_writer = PdfWriter()
    pdf_writer.append(io.BytesIO(bytes(base_pdf_bytes)))

    # 6. Processa Anexos (Somente se houver itens na lista)
    # A lógica de enviar lista vazia nas Fases 2 e 3 está no app.py, mas aqui garantimos que não quebra.
    if lista_anexos:
        print(f">>> PDF Generator: Anexando {len(lista_anexos)} arquivos...")
        for anexo in lista_anexos:
            filename = anexo['filename'].lower()
            stream = anexo['stream']
            
            try:
                if filename.endswith('.pdf'):
                    pdf_writer.append(PdfReader(stream))
                    print(f"    [OK] PDF anexado: {filename}")
                elif filename.endswith(('.jpg', '.jpeg', '.png')):
                    img = Image.open(stream)
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img_pdf = io.BytesIO()
                    img.save(img_pdf, format='PDF')
                    img_pdf.seek(0)
                    pdf_writer.append(PdfReader(img_pdf))
                    print(f"    [OK] Imagem anexada: {filename}")
            except Exception as e:
                print(f"    [ERRO] Falha ao anexar {filename}: {e}")
    else:
        print(">>> PDF Generator: Nenhum anexo para incluir.")

    # 7. Finaliza
    final_buffer = io.BytesIO()
    pdf_writer.write(final_buffer) 
    final_buffer.seek(0)
    
    print(">>> PDF Gerado com sucesso.")
    return final_buffer
