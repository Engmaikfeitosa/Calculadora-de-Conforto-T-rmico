import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pythermalcomfort.models import pmv_ppd
from pythermalcomfort.utilities import v_relative, clo_dynamic
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Conforto Térmico Pro - ISO 7730",
    page_icon="🌡️",
    layout="wide"
)

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; }
    .footer { position: fixed; bottom: 0; width: 100%; text-align: center; color: gray; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO ---
st.title("🌡️ Calculadora Profissional de Conforto Térmico")
st.markdown("Cálculo de **PMV** e **PPD** conforme as normas **ISO 7730** e **ASHRAE 55**.")
st.divider()

# --- BARRA LATERAL (ENTRADAS) ---
st.sidebar.header("📥 Parâmetros de Entrada")

with st.sidebar:
    st.subheader("🌡️ Condições Ambientais")
    ta = st.number_input("Temperatura do Ar (°C)", value=24.0, step=0.1)
    tr = st.number_input("Temperatura Radiante Média (°C)", value=24.0, step=0.1)
    vel = st.slider("Velocidade do Ar (m/s)", 0.0, 2.0, 0.1, 0.05)
    rh = st.slider("Umidade Relativa (%)", 0, 100, 50, 1)

    st.subheader("👤 Fatores Pessoais")
    met = st.selectbox("Atividade (Met)", 
                      options=[0.7, 1.0, 1.2, 1.4, 1.6, 2.0], 
                      index=2, 
                      help="0.7: Dormindo, 1.0: Sentado, 1.2: Escritório, 2.0: Caminhando")
    clo = st.number_input("Isolamento da Roupa (Clo)", value=0.6, step=0.1, 
                         help="Verão: 0.5, Inverno: 1.0")

# --- PROCESSAMENTO DOS DADOS ---
v_rel = v_relative(v=vel, met=met)
clo_d = clo_dynamic(clo=clo, met=met)

# Cálculo via biblioteca validada
res = pmv_ppd(tdb=ta, tr=tr, vr=v_rel, rh=rh, met=met, clo=clo_d, standard="ISO")
pmv = round(float(res['pmv']), 2)
ppd = round(float(res['ppd']), 1)

# --- LAYOUT PRINCIPAL (RESULTADOS) ---
col1, col2, col3 = st.columns([1, 1, 1.5])

with col1:
    st.metric("PMV (Voto Médio)", pmv)
    if -0.5 <= pmv <= 0.5:
        st.success("✅ Categoria A (Excelente)")
    elif -0.7 <= pmv <= 0.7:
        st.info("⚠️ Categoria B (Bom)")
    elif -1.0 <= pmv <= 1.0:
        st.warning("⚖️ Categoria C (Aceitável)")
    else:
        st.error("❌ Fora de Norma")

with col2:
    st.metric("PPD (% Insatisfeitos)", f"{ppd}%")
    # Pequeno gráfico de progresso para o PPD
    st.progress(min(ppd/100, 1.0))

with col3:
    # Gráfico Gauge do PMV
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = pmv,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [-3, 3], 'ticktext': ["Frio", "Neutro", "Quente"], 'tickvals': [-3, 0, 3]},
            'bar': {'color': "#333"},
            'steps': [
                {'range': [-3, -0.5], 'color': "#a5d6f7"},
                {'range': [-0.5, 0.5], 'color': "#8bc34a"},
                {'range': [0.5, 3], 'color': "#ff8a65"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': pmv}
        }
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

# --- ANÁLISE DE SENSIBILIDADE (GRÁFICO LINEAR) ---
st.subheader("📈 Sensibilidade Térmica")
st.caption("Como o PMV varia se a Temperatura do Ar mudar (mantendo os outros parâmetros fixos):")

temp_range = np.linspace(ta - 5, ta + 5, 20)
pmv_range = [pmv_ppd(tdb=t, tr=tr, vr=v_rel, rh=rh, met=met, clo=clo_d)['pmv'] for t in temp_range]
df_plot = pd.DataFrame({'Temp': temp_range, 'PMV': pmv_range})

fig_line = px.line(df_plot, x='Temp', y='PMV', labels={'Temp': 'Temperatura do Ar (°C)', 'PMV': 'PMV'})
fig_line.add_hline(y=0.5, line_dash="dash", line_color="orange", annotation_text="Limite Superior")
fig_line.add_hline(y=-0.5, line_dash="dash", line_color="orange", annotation_text="Limite Inferior")
fig_line.add_hline(y=0, line_color="green")
st.plotly_chart(fig_line, use_container_width=True)

# --- EXPORTAÇÃO E RELATÓRIO ---
st.divider()
st.subheader("📄 Exportar Resultados")

dados_finais = {
    "Parâmetro": ["Temp. Ar", "Temp. Radiante", "Vel. Ar", "Umidade", "Metabolismo", "Vestimenta", "PMV", "PPD"],
    "Valor": [ta, tr, vel, rh, met, clo, pmv, ppd],
    "Unidade": ["°C", "°C", "m/s", "%", "met", "clo", "-", "%"]
}
df_final = pd.DataFrame(dados_finais)

# Botão para baixar CSV
csv = df_final.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar Relatório em CSV",
    data=csv,
    file_name='relatorio_conforto_termico.csv',
    mime='text/csv',
)

st.table(df_final)

st.markdown("<div class='footer'>Desenvolvido para análise de Conforto Térmico - ISO 7730 / ASHRAE 55</div>", unsafe_allow_html=True)
