import pandas as pd

DUCTING_CSV = "/app/output/study-correlation/igra_ducts.csv"
PROPAGATION_CSV = "/app/output/study-correlation/daily_propagation_stats.csv"
MERGED_DATA = "/app/output/study-correlation/merged_data.csv"

def merge_ducting_propagation_data(ducting_file, propagation_file, output_file):
    # Charger les données
    df = pd.read_csv(ducting_file)
    df_propagation = pd.read_csv(propagation_file)
    
    # Convertir les colonnes date en datetime pour assurer une fusion correcte
    df['date'] = pd.to_datetime(df['date'], format='ISO8601').dt.strftime('%Y-%m-%d')
    df_propagation['date'] = pd.to_datetime(df_propagation['date'], format='ISO8601').dt.strftime('%Y-%m-%d')
    
    # Fusionner les données
    df_merged = pd.merge(df_propagation, df, on='date', how='outer')
    
    # Trier par date
    df_merged = df_merged.sort_values('date')
    
    # Sauvegarder le résultat
    df_merged.to_csv(output_file, index=False)
    print(f"Données fusionnées sauvegardées dans {output_file}")
    
    return df_merged

# Exemple d'utilisation
if __name__ == "__main__":
    # Fusionner les données
    merged_data = merge_ducting_propagation_data(DUCTING_CSV, PROPAGATION_CSV, MERGED_DATA)
    
    # Afficher un aperçu
    print("\nAperçu du tableau fusionné :")
    print(merged_data.head())