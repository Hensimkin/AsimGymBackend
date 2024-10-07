import pandas as pd
from sklearn.neighbors import NearestCentroid
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.cluster import KMeans
import scipy

# Load trainers data
df_trainers = pd.read_csv('Trainers.csv')

# Preprocess trainers data for clustering
# Encoding categorical variables: Gender and Fitness_Level
trainer_encoder = OneHotEncoder()
gender_fitness_encoded = trainer_encoder.fit_transform(df_trainers[['Gender', 'Fitness_Level']])

# Scaling numerical variables: Age, Height, Weight
scaler = StandardScaler()
age_height_weight_scaled = scaler.fit_transform(df_trainers[['Age', 'Height', 'Weight']])

# Combine scaled numerical and encoded categorical features
trainer_features = scipy.sparse.hstack([age_height_weight_scaled, gender_fitness_encoded])

# Perform K-Means clustering for trainers
optimal_clusters_trainers = 25  # You can change this number based on your preference
kmeans_trainers = KMeans(n_clusters=optimal_clusters_trainers, random_state=42)
df_trainers['Cluster'] = kmeans_trainers.fit_predict(trainer_features)

# Save updated trainers data with cluster information
df_trainers.to_csv('Trainers.csv', index=False)

# Save to a new CSV file
new_file_name = 'Updated_Trainers.csv'
df_trainers.to_csv(new_file_name, index=False)
print(f"Data with clusters saved to {new_file_name}")

# Print each trainer's information grouped by cluster
print("\nTrainer Information by Cluster:")
for cluster in sorted(df_trainers['Cluster'].unique()):
    print(f"\nCluster {cluster}\n" + "-"*25)
    cluster_data = df_trainers[df_trainers['Cluster'] == cluster]
    for index, row in cluster_data.iterrows():
        print(f"Trainer ID: {row['Trainer_id']}, "
              f"Fitness Level: {row['Fitness_Level']}, "
              f"Weight: {row['Weight']} kg, "
              f"Height: {row['Height']} cm, "
              f"Gender: {row['Gender']}, "
              f"Age: {row['Age']}, "
              f"Cluster: {row['Cluster']}")
    print("\n")  # Add extra space after each cluster

# Print the clusters and their counts
print("\nCluster distribution:")
cluster_counts = df_trainers['Cluster'].value_counts().sort_index()
for cluster, count in cluster_counts.items():
    print(f"Cluster {cluster}: {count} trainers")


def predict_user_cluster(age, height, weight, gender, fitness_level):
    gender = gender.capitalize()
    # Encode user's gender and fitness level using the same encoder as the trainers
    user_categorical_data = pd.DataFrame({'Gender': [gender], 'Fitness_Level': [fitness_level]})
    user_categorical_encoded = trainer_encoder.transform(user_categorical_data)

    # Scale user's age, height, and weight using the same scaler as the trainers
    user_numerical_data = pd.DataFrame({'Age': [age], 'Height': [height], 'Weight': [weight]})
    user_numerical_scaled = scaler.transform(user_numerical_data)

    # Combine encoded categorical and scaled numerical features
    user_features = scipy.sparse.hstack([user_numerical_scaled, user_categorical_encoded])

    # Predict the cluster for the user
    user_cluster = kmeans_trainers.predict(user_features)

    return user_cluster[0]


# Example usage of the function
user_age = 40
user_height = 180
user_weight = 75
user_gender = 'Male'
user_fitness_level = 'Beginner'

predicted_cluster = predict_user_cluster(user_age, user_height, user_weight, user_gender, user_fitness_level)
print(f"The user fits best in cluster {predicted_cluster}")