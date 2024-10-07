import pandas as pd

def process_list_and_csv(data_list, number):
    try:
        # Read the CSV file into a DataFrame
        df = pd.read_csv('clustered_exercises.csv')
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    # Initialize a dictionary to store results
    result = {}

    # Iterate over each body part in the data_list
    for body_part in data_list:
        # Filter rows where 'bodyPart' is equal to the current body part
        filtered_exercises = df[df['bodyPart'] == body_part]

        if not filtered_exercises.empty:
            # Find the maximum value in the specified column
            max_value = filtered_exercises[number].max()

            # Filter rows where the specified column has the maximum value
            max_exercises = filtered_exercises[filtered_exercises[number] == max_value]

            # Randomly select up to 3 rows from the filtered DataFrame
            if len(max_exercises) > 3:
                max_exercises = max_exercises.sample(n=3)

            # Get the list of exercise names
            exercise_names = max_exercises['name'].tolist()

            # Store the list in the result dictionary
            result[body_part] = exercise_names
        else:
            result[body_part] = []  # Store an empty list if no exercises are found

    return result

# Example usage
data = [ "back","chest"]
number = "23"  # Replace with the column you're looking for in the 'number' column
exercise_names_by_body_part = process_list_and_csv(data, number)

# Print the result
print(exercise_names_by_body_part)
