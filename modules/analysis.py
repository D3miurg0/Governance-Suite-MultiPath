import os
import glob
import warnings
from config import Config
from core.utils import Utils

try:
    import pandas as pd
    ANALYSIS_ENABLED = True
except ImportError:
    ANALYSIS_ENABLED = False

try:
    from xlsxwriter.utility import xl_col_to_name
except ImportError:
    pass

warnings.simplefilter(action='ignore', category=FutureWarning)


class AnalysisModule:
    """Consolida reportes CSV y genera Dashboard Excel con gráficas."""

    def __init__(self, core):
        self.core = core

    def generate_analysis_dashboard(self, analysis_dir: str):
        if not ANALYSIS_ENABLED:
            print("❌ ERROR: Instale pandas y xlsxwriter para usar esta función.")
            return
        base_search = os.path.join(analysis_dir, "**/*Reporte_*.csv")
        output_excel = os.path.join(analysis_dir, 'Reporte_Maestro_Analitico.xlsx')
        output_csv = os.path.join(analysis_dir, 'Datos_Consolidados_Full.csv')
        for f in [output_excel, output_csv]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as e:
                    self.core.log_error(f"No se pudo eliminar {f}: {e}", "FATAL")
                    return
        archivos_csv = glob.glob(base_search, recursive=True)
        if not archivos_csv:
            print("   [!] No se encontraron reportes CSV.")
            return
        lista_df = []
        for archivo in archivos_csv:
            try:
                lista_df.append(pd.read_csv(archivo, encoding='utf-8-sig'))
            except Exception as e:
                self.core.log_error(f"Error leyendo {archivo}: {e}", "ADVERTENCIA")
        if not lista_df:
            return
        df = pd.concat(lista_df, ignore_index=True)
        df['MB'] = pd.to_numeric(df['MB'], errors='coerce').fillna(0)
        df = df[df['MB'] >= 1.0].copy()
        df['TB'] = df['MB'] / (1024 * 1024)
        df['Extension'] = df['Nombre'].apply(Utils.get_extension)
        df['CarpetaPrincipal'] = df['Ruta_Completa'].apply(Utils.get_top_folder)
        df['Fecha_Mod'] = pd.to_datetime(df['Modificacion'], errors='coerce')
        df['Año'] = df['Fecha_Mod'].dt.year.fillna(0).astype(int)
        total_mb = df['MB'].sum()
        total_tb = total_mb / (1024 * 1024)
        total_archivos = len(df)
        type_summary = df.groupby('Extension')['MB'].sum().nlargest(10).reset_index()
        type_summary.columns = ['Tipo', 'Total_MB']
        location_summary = df.groupby('CarpetaPrincipal')['MB'].sum().nlargest(10).reset_index()
        location_summary.columns = ['Ubicacion', 'Total_MB']
        df_top10 = df.nlargest(10, 'MB')[['Nombre', 'MB', 'Ruta_Completa']]
        df.drop(columns=['Fecha_Mod']).to_csv(output_csv, index=False, encoding='utf-8-sig')
        try:
            writer = pd.ExcelWriter(output_excel, engine='xlsxwriter')
            wb = writer.book
            ws = wb.add_worksheet('Dashboard')
            bold = wb.add_format({'bold': True})
            ws.write('B4', 'Tamaño Total (TB):', bold)
            ws.write('C4', total_tb)
            ws.write('B5', 'Total Archivos (>= 1MB):', bold)
            ws.write('C5', total_archivos)
            ws.write('B7', 'Top 10 Archivos Pesados', wb.add_format({'bold': True, 'font_size': 14}))
            df_top10.to_excel(writer, sheet_name='Dashboard', startrow=8, startcol=1, index=False)
            type_summary.to_excel(writer, sheet_name='Data_Tipos', index=False)
            location_summary.to_excel(writer, sheet_name='Data_Ubicacion', index=False)
            chart_pie = wb.add_chart({'type': 'pie'})
            chart_pie.add_series({'name': 'Distribución', 'categories': '=Data_Tipos!$A$2:$A$12', 'values': '=Data_Tipos!$B$2:$B$12', 'data_labels': {'percentage': True}})
            chart_pie.set_title({'name': 'MB por Tipo de Archivo'})
            ws.insert_chart('B25', chart_pie, {'x_scale': 1.2, 'y_scale': 1.2})
            chart_bar = wb.add_chart({'type': 'bar'})
            chart_bar.add_series({'name': 'Top 10', 'categories': '=Data_Ubicacion!$A$2:$A$11', 'values': '=Data_Ubicacion!$B$2:$B$11'})
            chart_bar.set_title({'name': 'Top 10 Ubicaciones por MB'})
            chart_bar.set_legend({'position': 'none'})
            ws.insert_chart('K25', chart_bar, {'x_scale': 1.5, 'y_scale': 1.2})
            writer.sheets['Data_Tipos'].hide()
            writer.sheets['Data_Ubicacion'].hide()
            writer.close()
            print(f"   ✅ Dashboard generado: {output_excel}")
        except Exception as e:
            self.core.log_error(f"Error generando Excel: {e}", "FATAL")
