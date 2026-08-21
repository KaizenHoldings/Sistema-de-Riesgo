import streamlit as st
from utils import page_header

def show():
    page_header("function", "Fórmulas y Cálculos", "Detalle técnico del motor de riesgo", "KFG Risk Architect · Información")
    
    st.markdown("A continuación se detallan las fórmulas empleadas por el motor de riesgo (Risk Engine) para calificar y establecer la tasa de interés sugerida (Pricing) según el tipo de expediente.")
    
    # Corporativo
    st.subheader("1. Crédito Corporativo")
    st.markdown("El motor evalúa métricas financieras de las empresas para generar un score basado en liquidez, solvencia y cobertura.")
    
    st.markdown("#### 1.1 Indicadores Financieros")
    st.markdown("**DSCR (Debt Service Coverage Ratio):**\nMide la capacidad de la empresa para cubrir sus obligaciones con su flujo de caja operativo.")
    st.latex(r"DSCR = \frac{EBITDA}{Gastos\ Financieros + Cuota\ Anualizada}")
    
    st.markdown("#### 1.2 Score de Riesgo (1 a 10)")
    st.markdown("**Score Base ($S_{base}$):**")
    st.latex(r"S_{base} = \frac{(Score_{Liq} \cdot W_{liq}) + (Score_{Solv} \cdot W_{sol}) + (Score_{Cob} \cdot W_{cob})}{W_{liq} + W_{sol} + W_{cob}}")
    st.caption("*Donde W representa los pesos configurados por el administrador.*")
    
    st.markdown("**Ajuste Kaizen (AML/Compliance) ($S_{final}$):**")
    st.markdown("Si el cliente tiene un nivel de riesgo bajo en legitimación de capitales (Kaizen Compliance), su score recibe un 'boost' (mejora).")
    st.latex(r"S_{final} = \min\left( S_{base} \cdot \left(1 + \frac{Score_{KC}}{10} \cdot \%Boost\right), 10 \right)")
    
    st.markdown("#### 1.3 Política de Pricing (Tasa Sugerida)")
    st.markdown("El modelo de pricing penaliza los scores más bajos aumentando la tasa de interés base.")
    st.latex(r"Tasa = Tasa_{base} + (10 - S_{final}) \cdot Factor_{riesgo}")
    
    st.divider()
    
    # Automotriz
    st.subheader("2. Crédito Automotriz")
    st.markdown("Para la cartera de retail automotriz, el motor evalúa la capacidad de pago del individuo, el respaldo de la garantía y la estabilidad de ingresos.")
    
    st.markdown("#### 2.1 Indicadores de Crédito Retail")
    st.markdown("**LTV (Loan-to-Value):**\nMide el porcentaje de financiamiento frente al valor real del vehículo. Cuanto menor sea, menor es el riesgo.")
    st.latex(r"LTV = \left( \frac{Monto\ Solicitado}{Precio\ del\ Vehículo} \right) \times 100")
    
    st.markdown("**DTI Ratio (Debt-to-Income):**\nProporción de los ingresos mensuales que se comprometerán al pago del crédito.")
    st.latex(r"DTI = \left( \frac{Cuota\ Mensual}{Ingreso\ Mensual} \right) \times 100")
    
    st.markdown("#### 2.2 Score de Riesgo Automotriz")
    st.markdown("**Score Base ($S_{base}$):**")
    st.latex(r"S_{base} = \frac{(Score_{Cap} \cdot W_{cap}) + (Score_{LTV} \cdot W_{ltv}) + (Score_{Est} \cdot W_{est})}{W_{cap} + W_{ltv} + W_{est}}")
    st.markdown("""
    *Donde:*
    - **Cap:** Score de Capacidad de Pago (Basado inversamente en el DTI).
    - **LTV:** Score Loan-to-Value (Basado en el aporte inicial o enganche).
    - **Est:** Score Nivel de estabilidad laboral (Cualitativo).
    """)
    
    st.markdown("**Ajuste Kaizen (AML/Compliance) ($S_{final}$):**")
    st.latex(r"S_{final} = \min\left( S_{base} \cdot \left(1 + \frac{Score_{KC}}{10} \cdot \%Boost\ Auto\right), 10 \right)")
    
    st.markdown("#### 2.3 Política de Pricing Automotriz")
    st.markdown("Calcula la tasa recomendada para el financiamiento del vehículo ajustada al riesgo del individuo.")
    st.latex(r"Tasa = Tasa_{base\ Auto} + (10 - S_{final}) \cdot Factor_{riesgo\ Auto}")
    
    st.info("Modificadores Configurables: Todos los pesos (W), %Boost, Tasa base y Factor de riesgo pueden ser modificados en tiempo real desde la sección **Parámetros** sin necesidad de alterar el código del motor.")
