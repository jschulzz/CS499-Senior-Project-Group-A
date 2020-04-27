import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn import metrics
from sklearn import tree
from sklearn.metrics import confusion_matrix

# Importing the dataset (sort it by relevancy)
dataset = pd.read_csv('data/coded_full_tweets.csv').sort_values('relevancy')
X = dataset.iloc[-100:, :-1].values
y = dataset.iloc[-100:, -1].values

# transform certain fields so that they are usable during training
for idx in range(X.shape[0]):
    readingLevel = X[idx, 64].split()[0][:-2]
    X[idx, 64] = readingLevel

# get useful fields from x (columns 19-30 and 53-69)
usefulX = X[:, np.r_[19:30, 53:69]]

# create testing and training datasets
X_train, X_test, y_train, y_test = train_test_split(usefulX, y, test_size=0.3)

# train regression model
for i in range(20):
    # create a minibatch
    batchIndices = np.random.choice(X_train.shape[0], 30, replace=False)
    X_batch, y_batch = X_train[batchIndices], y_train[batchIndices]

    # train on minibatch
    regressor = tree.DecisionTreeRegressor()
    regressor.fit(X_batch, y_batch)

    # test trained model
    y_pred = regressor.predict(X_test)
    MAE = metrics.mean_absolute_error(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    print("Iteration %d" % (i+1))
    print("\tPrediction: ", np.ndarray.astype(y_pred, int))
    print("\tReal:       ", y_test)

    print("\t%.5f" % MAE)
    print("\tType I Error: %d" % fp)
    print("\tType II Error: %d" % fn)