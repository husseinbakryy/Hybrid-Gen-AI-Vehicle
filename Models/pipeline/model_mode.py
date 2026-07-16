from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.svm import LinearSVC



def train_mode_model(X_train, X_test, y_train, y_test):
    base_svc = LinearSVC(C=0.1, random_state=42, max_iter=2000, dual=False)
    model = CalibratedClassifierCV(base_svc)
    model.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))

    return model, {"train_accuracy": train_acc, "test_accuracy": test_acc}
