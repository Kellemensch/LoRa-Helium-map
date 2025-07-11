from collections import defaultdict
import pandas as pd

DATA_FILE = "/app/output/data/helium_gateway_data.csv"
OUTPUT_STATS = "/app/output/study-correlation/daily_propagation_stats.csv"


def calculate_daily_propagation_stats():
    try:
        df = pd.read_csv(DATA_FILE)
        df['date'] = pd.to_datetime(df['gwTime'], format='ISO8601').dt.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return

    # Dictionnaire pour stocker les stats par jour
    daily_stats = defaultdict(lambda: {
        'total_links': 0,
        'nlos_links': 0,
        'sum_distance': 0,
        'max_distance': 0,
        'gateways': set(),
        'end_nodes': set()
    })

    # Calculer les statistiques
    for _, row in df.iterrows():
        date = row['date']
        stats = daily_stats[date]
        
        stats['total_links'] += 1
        stats['sum_distance'] += float(row['dist_km'])
        
        if float(row['dist_km']) > stats['max_distance']:
            stats['max_distance'] = float(row['dist_km'])
        
        if str(row['visibility']) == "NLOS":
            stats['nlos_links'] += 1
        
        stats['gateways'].add(row['gatewayId'])

    results = []
    for date, stats in sorted(daily_stats.items()):
        avg_distance = stats['sum_distance'] / stats['total_links'] if stats['total_links'] > 0 else 0
        nlos_ratio = stats['nlos_links'] / stats['total_links'] if stats['total_links'] > 0 else 0
        
        results.append({
            'date': date,
            'total_links': stats['total_links'],
            'nlos_links': stats['nlos_links'],
            'nlos_ratio': round(nlos_ratio, 3),
            'avg_distance_km': round(avg_distance, 2),
            'max_distance_km': round(stats['max_distance'], 2),
            'unique_gateways': len(stats['gateways']),
        })

    # Sauvegarder en CSV
    df_results = pd.DataFrame(results)
    df_results.to_csv(OUTPUT_STATS, index=False)
    print(f"Statistiques sauvegardées dans {OUTPUT_STATS}")

    return df_results

if __name__ == "__main__":
    stats = calculate_daily_propagation_stats()
    print(stats.head())