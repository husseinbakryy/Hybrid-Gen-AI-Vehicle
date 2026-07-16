from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score



def train_battery_model(X_train, X_test, y_train, y_test):
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=15,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_r2 = r2_score(y_train, model.predict(X_train))
    test_r2 = r2_score(y_test, model.predict(X_test))

    return model, {"train_r2": train_r2, "test_r2": test_r2}
