import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.cluster import KMeans
import scipy
from sklearn.metrics import silhouette_score
#this code is in clustering
# Load your data into a DataFrame
df = pd.read_csv('exercises.csv')

# Combine all instruction columns into a single 'instructions' column
instruction_columns = [col for col in df.columns if 'instructions/' in col]
df['instructions'] = df[instruction_columns].fillna('').agg(' '.join, axis=1)

# Feature extraction
tfidf = TfidfVectorizer(stop_words='english')
instruction_vectors = tfidf.fit_transform(df['instructions'])

# One-hot encode the target, secondaryMuscles, and bodyPart
encoder = OneHotEncoder()
encoded_features = encoder.fit_transform(df[['target', 'secondaryMuscles/0', 'secondaryMuscles/1', 'bodyPart']])

# Combine the features
combined_features = scipy.sparse.hstack([instruction_vectors, encoded_features])

# Perform K-Means Clustering
num_clusters = 50  # Set the number of clusters
kmeans = KMeans(n_clusters=num_clusters, random_state=42)
df['cluster'] = kmeans.fit_predict(combined_features)

# Calculate and display Silhouette Score
silhouette_avg = silhouette_score(combined_features, df['cluster'])
print(f"Silhouette Score: {silhouette_avg}")

print(f"Inertia: {kmeans.inertia_}")
# Display the clustered exercises with more details
i=0
for cluster in range(num_clusters):
    print(f"Exercises in Cluster {cluster + 1}:")
    cluster_exercises = df[df['cluster'] == cluster]
    for index, row in cluster_exercises.iterrows():
        i+=1
        print(f" - {row['name']} ({row['bodyPart']}) ({row['target']}) ({row['secondaryMuscles/1']}) ({row['secondaryMuscles/0']}) ({row['equipment']}) (Exercise ID: {row['id']})")
    print("\n" + "="*50 + "\n")

print(i)

print(f"Silhouette Score: {silhouette_avg}")

print(f"Inertia: {kmeans.inertia_}")