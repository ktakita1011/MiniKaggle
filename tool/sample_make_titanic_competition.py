from pathlib import Path

import pandas as pd
from sklearn.datasets import fetch_openml
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

OUTPUT_DIR = Path("../competition")
DISTRIBUSION_DIR = OUTPUT_DIR / "distribution"
DISTRIBUSION_DIR.mkdir(parents=True, exist_ok=True)

# Load Titanic dataset from sklearn
titanic = fetch_openml("titanic", version=1, as_frame=True)

all_df = titanic.data
all_df["survived"] = titanic.target


train_data, test_data = train_test_split(all_df, test_size=0.3, random_state=32)
train_data = train_data.reset_index(drop=True)
test_data = test_data.reset_index(drop=True)
train_data["id"] = train_data.index
test_data["id"] = test_data.index


# Preprocess the data
def preprocess_data(data):
    # Drop unnecessary columns
    data = data.drop(["name", "ticket", "cabin", "home.dest"], axis=1)

    # Encode categorical variables
    le = LabelEncoder()
    for col in ["sex", "embarked", "boat"]:
        data[col] = le.fit_transform(data[col].astype(str))

    # Handle missing values
    data["embarked"] = data["embarked"].fillna(data["embarked"].mode()[0])
    data["age"] = data["age"].fillna(data["age"].median())
    data["fare"] = data["fare"].fillna(data["fare"].median())
    data["boat"] = data["boat"].fillna(data["boat"].median())
    data["body"] = data["body"].fillna(data["body"].median())

    return data


train_data = preprocess_data(train_data)
test_data = preprocess_data(test_data)

# Create is_public column with half 0s and half 1s
test_data["is_public"] = [0] * (len(test_data) // 2) + [1] * (
    len(test_data) - len(test_data) // 2
)

# Separate features and target
X = train_data.drop(["survived"], axis=1)
y = train_data["survived"]

# Split the data into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.4, random_state=42)

# Train the model
model = DecisionTreeClassifier(max_depth=5, min_samples_split=2, random_state=42)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_val)

# Evaluate the model
accuracy = accuracy_score(y_val, y_pred)
print(f"Validation Accuracy: {accuracy}")

# Perform cross-validation
cv_scores = cross_val_score(model, X, y, cv=5)
print(f"Cross-validation scores: {cv_scores}")
print(f"Mean CV score: {cv_scores.mean()}")

# Make predictions on the test data
X_test = test_data.drop(["survived", "is_public"], axis=1)
test_predictions = model.predict(X_test)

# Add predictions to the test_data dataframe
test_data["Predicted_Survived"] = test_predictions
print(test_data[["id", "Predicted_Survived"]])

# Create submission DataFrame
submission = pd.DataFrame({"id": test_data["id"], "survived": test_predictions})

# Save to CSV file
submission.to_csv(DISTRIBUSION_DIR / "sample_submission.csv", index=False)
train_data.to_csv(DISTRIBUSION_DIR / "train.csv", index=False)
test_data.drop(["is_public", "survived", "Predicted_Survived"], axis=1).to_csv(
    DISTRIBUSION_DIR / "test.csv", index=False
)
test_data.drop(["Predicted_Survived"], axis=1).to_csv(
    OUTPUT_DIR / "test_answer.csv", index=False
)

print("Submission file has been created.")
