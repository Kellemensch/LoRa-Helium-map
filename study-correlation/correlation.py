import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats
import numpy as np
from sklearn.linear_model import LinearRegression
import seaborn as sns
import os

# Configuration initiale
os.makedirs("/app/web/static/stats", exist_ok=True)
IMG_DIR = "/app/web/static/stats/"
MERGED_DATA = "/app/output/study-correlation/merged_data.csv"

# Style des graphiques
# plt.style.use('seaborn')
# sns.set_palette("husl")

def save_plot(filename):
    """Sauvegarde la figure actuelle et nettoie"""
    plt.tight_layout()
    plt.savefig(f"{IMG_DIR}{filename}")
    plt.close()  # Ferme la figure actuelle
    plt.clf()    # Nettoie le buffer

# Chargement des données
df = pd.read_csv(MERGED_DATA)
df = df[df["total_links"].notna() & df["min_gradient"].notna()]
df = df[df["min_gradient"] > -1300]

# 1. Correlation Spearman - max distance
plt.figure(figsize=(10, 6))
y, x = df["min_gradient"], df["max_distance_km"]
rho, _ = scipy.stats.spearmanr(x, y)
plt.scatter(x, y, alpha=0.6)
plt.plot(np.sort(x), np.sort(y), color='red', linestyle='--')
plt.title(f"Spearman Correlation: {rho:.2f}\nMin Gradient vs Max Distance")
plt.ylabel("Min Gradient")
plt.xlabel("Max Distance (km)")
save_plot("spearman_maxdist.png")

# 2. Correlation Spearman - NLOS ratio
plt.figure(figsize=(10, 6))
y, x = df["min_gradient"], df["nlos_ratio"]
rho, _ = scipy.stats.spearmanr(x, y)
plt.scatter(x, y, alpha=0.6)
plt.plot(np.sort(x), np.sort(y), color='red', linestyle='--')
plt.title(f"Spearman Correlation: {rho:.2f}\nMin Gradient vs NLOS Ratio")
plt.ylabel("Min Gradient")
plt.xlabel("NLOS Ratio")
save_plot("spearman_nlosratio.png")

# 3. Correlation Spearman - NLOS links
plt.figure(figsize=(10, 6))
y, x = df["min_gradient"], df["nlos_links"]
rho, _ = scipy.stats.spearmanr(x, y)
plt.scatter(x, y, alpha=0.6)
plt.plot(np.sort(x), np.sort(y), color='red', linestyle='--')
plt.title(f"Spearman Correlation: {rho:.2f}\nMin Gradient vs NLOS Links")
plt.ylabel("Min Gradient")
plt.xlabel("NLOS Links Count")
save_plot("spearman_nloslinks.png")

# 4. Correlation Spearman - avg distance
plt.figure(figsize=(10, 6))
y, x = df["min_gradient"], df["avg_distance_km"]
rho, _ = scipy.stats.spearmanr(x, y)
plt.scatter(x, y, alpha=0.6)
plt.plot(np.sort(x), np.sort(y), color='red', linestyle='--')
plt.title(f"Spearman Correlation: {rho:.2f}\nMin Gradient vs Avg Distance")
plt.ylabel("Min Gradient")
plt.xlabel("Average Distance (km)")
save_plot("spearman_avgdist.png")

# 5. Correlation Pearson - max distance
plt.figure(figsize=(10, 6))
y, x = df["min_gradient"], df["max_distance_km"]
rho, _ = scipy.stats.pearsonr(x, y)
plt.scatter(x, y, alpha=0.6)
plt.plot(np.sort(x), np.sort(y), color='blue', linestyle='--')
plt.title(f"Pearson Correlation: {rho:.2f}\nMin Gradient vs Max Distance")
plt.ylabel("Min Gradient")
plt.xlabel("Max Distance (km)")
save_plot("pearson_maxdist.png")

# 6. Régression linéaire
plt.figure(figsize=(10, 6))
model = LinearRegression()
x, y = df[["min_gradient"]], df["max_distance_km"]
model.fit(x, y)
sns.regplot(x="min_gradient", y="max_distance_km", data=df, 
            scatter_kws={'alpha':0.6},
            line_kws={'color':'red'})
plt.title(f"Linear Regression\nSlope: {model.coef_[0]:.2f}, Intercept: {model.intercept_:.2f}")
plt.ylabel("Max Distance (km)")
plt.xlabel("Min Gradient")
save_plot("linearreg_maxdist.png")

# 7. Analyse temporelle
plt.figure(figsize=(12, 6))
sns.lineplot(x="date", y="max_distance_km", data=df, 
             estimator='mean', errorbar=None)
plt.title("Temporal Analysis of Max Distance")
plt.ylabel("Max Distance (km)")
plt.xlabel("Date")
plt.xticks(rotation=45)
save_plot("temporal_analysis.png")

# 8. Matrice de corrélation
plt.figure(figsize=(10, 8))
cols = ['total_links', 'nlos_links', 'avg_distance_km', 
        'max_distance_km', 'min_gradient', 'duct_present']
sns.heatmap(df[cols].corr(), annot=True, cmap='coolwarm', 
            center=0, fmt=".2f", linewidths=.5)
plt.title("Correlation Matrix")
save_plot("correlation_matrix.png")

# 9. Ratio NLOS vs Gradient
plt.figure(figsize=(10, 6))
sns.regplot(x='nlos_links', y='min_gradient', data=df,
            scatter_kws={'alpha':0.6},
            line_kws={'color':'red'})
plt.title("NLOS Links vs Min Gradient")
plt.ylabel("Min Gradient")
plt.xlabel("NLOS Links Count")
save_plot("nlosratio_gradient.png")