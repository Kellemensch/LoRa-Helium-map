import datetime
import pandas as pd
import os


FIRST_DAY = datetime.datetime.strptime("2025-06-28", '%Y-%m-%d')
END_DAY = datetime.datetime.today()

IMG_DIR = "/app/web/static/stats/"

IGRA_FTP = "ftp://ftp.ncei.noaa.gov/pub/data/igra/derived/derived-por/"
IGRA_FILE = "/app/output/igra-datas/derived/ITM00016045-drvd.txt"
STATIONS_FILE = "/app/output/igra-datas/igra2-station-list.txt"
OUTPUT_CSV = "/app/output/study-correlation/igra_ducts.csv"

os.makedirs("/app/output/study-correlation/", exist_ok=True)

DUCT_THRESHOLD = -157

def parse_igra_derived_file(filepath, target_year, target_month, target_day):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    data = []
    current_sounding = None
    inside_target_day = False

    for line in lines:
        if line.startswith('#'):
            year = int(line[13:17])
            month = int(line[18:20])
            day = int(line[21:23])

            if year == target_year and month == target_month and day == target_day:
                inside_target_day = True
                if current_sounding:
                    data.append(current_sounding)
                current_sounding = {'date': (year, month, day), 'levels': []}
            else:
                inside_target_day = False
        elif inside_target_day and current_sounding:
            try:
                height = int(line[16:23].strip())
                N = int(line[144:151].strip())
                if height != -99999 and N != -99999:
                    current_sounding['levels'].append((height, N))
            except ValueError:
                continue
            except ValueError:
                continue

    if current_sounding and current_sounding['levels']:
        data.append(current_sounding)

    return data

def compute_gradients(levels):
    gradients = []
    for i in range(len(levels) - 1):
        h1, N1 = levels[i]
        h2, N2 = levels[i + 1]
        if h2 != h1:
            dN_dh = (N2 - N1) / (h2 - h1) * 1000  # N/km
            gradients.append((h1, dN_dh))
    return gradients


def detect_duct_zones(gradients, threshold = DUCT_THRESHOLD):
    duct_zones = []
    current_duct = None
    
    for h, g in gradients:
        if g < threshold:
            if current_duct is None:
                # Start new duct zone
                current_duct = {
                    'base_height': h,
                    'top_height': h,
                    'min_gradient': g,
                    'min_gradient_height': h
                }
            else:
                # Extend existing duct zone
                current_duct['top_height'] = h
                if g < current_duct['min_gradient']:
                    current_duct['min_gradient'] = g
                    current_duct['min_gradient_height'] = h
        else:
            if current_duct is not None:
                # Finalize current duct zone
                current_duct['thickness'] = current_duct['top_height'] - current_duct['base_height']
                duct_zones.append(current_duct)
                current_duct = None
    
    # Add last duct if file ends with duct
    if current_duct is not None:
        current_duct['thickness'] = current_duct['top_height'] - current_duct['base_height']
        duct_zones.append(current_duct)
    
    return duct_zones

def analyze_ducting_for_date(date):
    data = parse_igra_derived_file(
        IGRA_FILE, 
        date.year, 
        date.month, 
        date.day
    )
    
    if not data or not data[0]['levels']:
        return None
    
    gradients = compute_gradients(data[0]['levels'])
    duct_zones = detect_duct_zones(gradients)
    
    result = {
        'date': date.strftime('%Y-%m-%d'),
        'duct_present': len(duct_zones) > 0,
        'num_ducts': len(duct_zones),
        'min_gradient': 0,
        'ducts': []
    }
    
    min_gradient = 0
    for i, duct in enumerate(duct_zones, 1):
        duct_info = {
            f'duct_{i}_base_height': duct['base_height'],
            f'duct_{i}_top_height': duct['top_height'],
            f'duct_{i}_thickness': duct['thickness'],
            f'duct_{i}_min_gradient': duct['min_gradient'],
            f'duct_{i}_min_gradient_height': duct['min_gradient_height']
        }
        result.update(duct_info)
        result['ducts'].append(duct)
        if duct['min_gradient'] < min_gradient:
            min_gradient = duct['min_gradient']

    result['min_gradient'] = min_gradient

    return result

def main():
    results = []
    current_date = FIRST_DAY

    while current_date <= END_DAY:
        print(f"Processing {current_date.strftime('%Y-%m-%d')}...")
        analysis = analyze_ducting_for_date(current_date)
        
        if analysis is None:
            print(f"No data for {current_date.strftime('%Y-%m-%d')}")
            current_date += datetime.timedelta(days=1)
            continue
        
        # Prepare flat record for CSV
        record = {
            'date': analysis['date'],
            'duct_present': analysis['duct_present'],
            'num_ducts': int(analysis['num_ducts']),
            'min_gradient': float(analysis['min_gradient'])
        }
        
        # Add duct information
        for i in range(1, analysis['num_ducts'] + 1):
            record.update({
                f'duct_{i}_base_height': analysis[f'duct_{i}_base_height'],
                f'duct_{i}_top_height': analysis[f'duct_{i}_top_height'],
                f'duct_{i}_thickness': analysis[f'duct_{i}_thickness'],
                f'duct_{i}_min_gradient': analysis[f'duct_{i}_min_gradient'],
                f'duct_{i}_min_gradient_height': analysis[f'duct_{i}_min_gradient_height']
            })
        
        results.append(record)
        current_date += datetime.timedelta(days=1)
    
    # Save results to CSV
    df = pd.DataFrame(results)
    
    # Reorder columns for better readability
    columns = ['date', 'duct_present', 'num_ducts', 'min_gradient']
    max_ducts = df['num_ducts'].max() if not df.empty else 0
    
    for i in range(1, max_ducts + 1):
        columns.extend([
            f'duct_{i}_base_height',
            f'duct_{i}_top_height',
            f'duct_{i}_thickness',
            f'duct_{i}_min_gradient',
            f'duct_{i}_min_gradient_height'
        ])
    
    df = df.reindex(columns=columns)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Ducting analysis saved to {OUTPUT_CSV}")

main()