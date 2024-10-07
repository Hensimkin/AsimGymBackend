import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import scipy
from sklearn.metrics import silhouette_score

# Step 1: Load data and preprocess for clustering

# Load trainers data
df_trainers = pd.read_csv('trainers.csv')

# Preprocess trainers data for clustering
trainer_encoder = OneHotEncoder()
gender_encoded = trainer_encoder.fit_transform(df_trainers[['Gender']])
scaler = StandardScaler()
age_height_scaled = scaler.fit_transform(df_trainers[['Age', 'Height']])
trainer_features = scipy.sparse.hstack([age_height_scaled, gender_encoded])

# Perform K-Means clustering for trainers
optimal_clusters_trainers = 16  # Assuming 16 clusters is optimal based on previous analysis
kmeans_trainers = KMeans(n_clusters=optimal_clusters_trainers, random_state=42)
df_trainers['Cluster'] = kmeans_trainers.fit_predict(trainer_features)

# Save updated trainers data with cluster information
df_trainers.to_csv('trainers.csv', index=False)

# Load exercises data
df_exercises = pd.read_csv('exercises.csv')

# Combine all instruction columns into a single 'instructions' column
instruction_columns = [col for col in df_exercises.columns if 'instructions/' in col]
df_exercises['instructions'] = df_exercises[instruction_columns].fillna('').agg(' '.join, axis=1)

# Feature extraction for exercises
tfidf = TfidfVectorizer(stop_words='english')
instruction_vectors = tfidf.fit_transform(df_exercises['instructions'])

# One-hot encode the target, secondaryMuscles, and bodyPart
exercise_encoder = OneHotEncoder()
encoded_exercise_features = exercise_encoder.fit_transform(
    df_exercises[['target', 'secondaryMuscles/0', 'secondaryMuscles/1',
                  'secondaryMuscles/2', 'secondaryMuscles/3',
                  'secondaryMuscles/4', 'secondaryMuscles/5',
                  'bodyPart']])

# Combine the features for exercises
combined_exercise_features = scipy.sparse.hstack([instruction_vectors, encoded_exercise_features])

# Perform K-Means clustering for exercises
optimal_clusters = 19
kmeans_exercises = KMeans(n_clusters=optimal_clusters, random_state=42)
df_exercises['cluster'] = kmeans_exercises.fit_predict(combined_exercise_features)

# Calculate and display Silhouette Score for exercises
silhouette_avg_exercises = silhouette_score(combined_exercise_features, df_exercises['cluster'])
print(f"Silhouette Score for exercises: {silhouette_avg_exercises}")


# Step 2: User Recommendation System

def get_user_cluster(user_id):
    # Get user's data based on ID
    user_data = df_trainers[df_trainers['Trainer_id'] == user_id]
    if user_data.empty:
        raise ValueError(f"No trainer found with ID {user_id}")

    user_age = user_data['Age'].values[0]
    user_height = user_data['Height'].values[0]
    user_gender = user_data['Gender'].values[0]

    # Preprocess the user's data to determine their cluster
    user_data_df = pd.DataFrame([[user_age, user_height, user_gender]], columns=['Age', 'Height', 'Gender'])
    user_gender_encoded = trainer_encoder.transform(user_data_df[['Gender']])
    user_age_height_scaled = scaler.transform(user_data_df[['Age', 'Height']])
    user_features = scipy.sparse.hstack([user_age_height_scaled, user_gender_encoded])
    user_cluster = kmeans_trainers.predict(user_features)[0]
    return user_cluster


def recommend_exercises(muscle_groups, user_cluster):
    # Filter exercises by muscle groups
    filtered_exercises = df_exercises[df_exercises['bodyPart'].isin(muscle_groups)]

    if not filtered_exercises.empty:
        # Sort by 'cluster{user_cluster}_rating' with highest rating first
        if f'cluster{user_cluster}_rating' in filtered_exercises.columns:
            filtered_exercises = filtered_exercises.sort_values(by=f'cluster{user_cluster}_rating', ascending=False)

        # Determine the number of exercises to return based on the number of muscle groups
        num_muscle_groups = len(muscle_groups)
        if num_muscle_groups == 1:
            # Return all top 8 exercises from the single muscle group
            recommended_exercises = filtered_exercises.head(8)
        elif num_muscle_groups == 2:
            # Distribute 4 exercises from each muscle group
            exercises_per_group = []
            for muscle_group in muscle_groups:
                group_exercises = filtered_exercises[filtered_exercises['bodyPart'] == muscle_group]
                exercises_per_group.append(group_exercises.head(4))
            recommended_exercises = pd.concat(exercises_per_group).head(8)
        elif num_muscle_groups == 3:
            # Distribute 3 exercises from each of the first two muscle groups and 2 from the third
            exercises_per_group = []
            for i, muscle_group in enumerate(muscle_groups):
                group_exercises = filtered_exercises[filtered_exercises['bodyPart'] == muscle_group]
                if i < 2:
                    exercises_per_group.append(group_exercises.head(3))
                else:
                    exercises_per_group.append(group_exercises.head(2))
            recommended_exercises = pd.concat(exercises_per_group).head(8)
    else:
        # If no exercises have ratings, perform a random pick from the filtered exercises
        if len(filtered_exercises) > 0:
            random_exercises = filtered_exercises.sample(n=8, replace=True)
        else:
            # If there are no filtered exercises, pick randomly from the entire dataset
            random_exercises = df_exercises.sample(n=8, replace=True)
        recommended_exercises = random_exercises

    return recommended_exercises


def collect_feedback_and_update(exercise_list, user_cluster):
    while True:
        new_exercise_list = []
        exercises_loved = []
        exercises_liked = []
        exercises_to_replace = []

        # First pass: collect feedback
        for index, exercise in exercise_list.iterrows():
            feedback = input(
                f"How did you like the exercise {exercise['name']}? (loved, like, moderate, dislike): ").lower()

            if feedback == "loved":
                df_exercises.loc[index, f'cluster{user_cluster}_rating'] += 2
                new_exercise_list.append(exercise)
                exercises_loved.append(exercise)
            elif feedback == "like":
                df_exercises.loc[index, f'cluster{user_cluster}_rating'] += 1
                new_exercise_list.append(exercise)
                exercises_liked.append(exercise)
            elif feedback == "moderate":
                df_exercises.loc[index, f'cluster{user_cluster}_rating'] -= 1
                if input("Would you like to replace this exercise? (yes/no): ").lower() == "yes":
                    exercises_to_replace.append(exercise)
                else:
                    new_exercise_list.append(exercise)
            elif feedback == "dislike":
                df_exercises.loc[index, f'cluster{user_cluster}_rating'] -= 2
                exercises_to_replace.append(exercise)

        # If there are exercises to replace, suggest replacements
        if exercises_to_replace:
            replacement_suggestions = []
            for loved_exercise in exercises_loved:
                count = 2
                replacement_suggestions.extend(
                    get_replacement_exercise(loved_exercise, user_cluster, count))
            for liked_exercise in exercises_liked:
                count = 1
                replacement_suggestions.extend(
                    get_replacement_exercise(liked_exercise, user_cluster, count))

            # Remove duplicates from the suggestions
            replacement_suggestions = pd.DataFrame(replacement_suggestions).drop_duplicates().reset_index(drop=True)

            # Keep suggesting replacements until all exercises are replaced
            for exercise_to_replace in exercises_to_replace:
                while True:
                    print(f"\nYou chose to replace the exercise {exercise_to_replace['name']}.")
                    print("Here are your replacement options:")

                    for i, suggestion in replacement_suggestions.iterrows():
                        print(f"{i + 1}. {suggestion['name']} (Target: {suggestion['target']}, Equipment: {suggestion['equipment']})")

                    choice = int(input("Choose an exercise to replace (enter the number): ")) - 1
                    if 0 <= choice < len(replacement_suggestions):
                        selected_exercise = replacement_suggestions.iloc[choice]
                        new_exercise_list.append(selected_exercise)

                        # Remove the selected exercise from suggestions
                        replacement_suggestions = replacement_suggestions.drop(choice).reset_index(drop=True)

                        # Refill suggestions based on loved/liked exercises
                        for loved_exercise in exercises_loved:
                            count = 2 - len(replacement_suggestions)
                            if count > 0:
                                replacement_suggestions = pd.concat([replacement_suggestions,
                                                                     get_replacement_exercise(loved_exercise, user_cluster, count)]).drop_duplicates().reset_index(drop=True)
                        for liked_exercise in exercises_liked:
                            count = 1 - len(replacement_suggestions)
                            if count > 0:
                                replacement_suggestions = pd.concat([replacement_suggestions,
                                                                     get_replacement_exercise(liked_exercise, user_cluster, count)]).drop_duplicates().reset_index(drop=True)
                        break
                    else:
                        print("Invalid choice. Please select a valid option.")

        # Print final workout
        print("\nFinal Workout Plan:")
        for exercise in new_exercise_list:
            print(f"Exercise Name: {exercise['name']}")
            print(f"Target Muscle: {exercise['target']}")
            secondary_muscles = ', '.join([str(exercise.get(f'secondaryMuscles/{i}', '')) for i in range(6)])
            print(f"Secondary Muscles: {secondary_muscles}")
            print(f"Equipment: {exercise['equipment']}")
            print("Instructions:")
            instructions = exercise['instructions'].split('.')
            for step_num, step in enumerate(instructions, 1):
                if step.strip():
                    print(f"  Step {step_num}: {step.strip()}")
            print("-" * 50)

        # Ask for feedback on the final workout
        if input("Are you satisfied with the workout? (yes/no): ").lower() == "yes":
            break

        # Update exercise_list for the next iteration if the user wants to make more changes
        exercise_list = pd.DataFrame(new_exercise_list)

    return new_exercise_list



def get_replacement_exercise(old_exercise, user_cluster, count):
    # Recommend replacement exercises
    similar_exercises = df_exercises[
        (df_exercises['cluster'] == old_exercise['cluster']) &
        (df_exercises['bodyPart'] == old_exercise['bodyPart']) &
        (df_exercises['target'] == old_exercise['target']) &
        (df_exercises['id'] != old_exercise['id'])
        ]

    sorted_similar_exercises = similar_exercises.sort_values(by=f'cluster{user_cluster}_rating', ascending=False)

    # Ensure that we return a list of pandas Series objects
    replacement_suggestions = sorted_similar_exercises.head(count).to_dict('records')

    return [pd.Series(suggestion) for suggestion in replacement_suggestions]


def main():
    # Ask for trainer ID
    trainer_id = int(input("Enter your trainer ID: "))

    # Get user's cluster
    user_cluster = get_user_cluster(trainer_id)

    # Ask for muscle group preferences
    muscle_groups = input("Enter muscle groups you want to train (comma-separated): ").split(',')
    muscle_groups = [group.strip() for group in muscle_groups]

    # Recommend exercises
    initial_recommendation = recommend_exercises(muscle_groups, user_cluster)

    # Print recommended exercises with full information
    print("\nRecommended Exercises:")
    for exercise in initial_recommendation.itertuples(index=False):
        print(f"Exercise Name: {exercise.name}")
        print(f"Target Muscle: {exercise.target}")
        print(f"Secondary Muscles: {exercise.all_secondary_muscles}")
        print(f"Equipment: {exercise.equipment}")
        print("Instructions:")
        instructions = getattr(exercise, 'instructions', '').split('.')
        for step_num, step in enumerate(instructions, 1):
            if step.strip():
                print(f"  Step {step_num}: {step.strip()}")
        print("-" * 50)

    # Collect feedback and update
    feedback_updated_exercises = collect_feedback_and_update(initial_recommendation, user_cluster)

    # Display updated exercises
    print("\nUpdated Exercise Recommendations:")
    for exercise in feedback_updated_exercises:
        print(f"Exercise Name: {exercise['name']}")
        print(f"Target Muscle: {exercise['target']}")
        secondary_muscles = ', '.join([str(exercise.get(f'secondaryMuscles/{i}', '')) for i in range(6)])
        print(f"Secondary Muscles: {secondary_muscles}")
        print(f"Equipment: {exercise['equipment']}")
        print("Instructions:")
        instructions = exercise['instructions'].split('.')
        for step_num, step in enumerate(instructions, 1):
            if step.strip():
                print(f"  Step {step_num}: {step.strip()}")
        print("-" * 50)

# if __name__ == "__main__":
#     main()