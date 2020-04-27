import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.metrics import confusion_matrix
from sklearn.linear_model import LinearRegression
import pickle

# Importing the dataset (sort it by relevancy)
dataset = pd.read_csv('data/coded_full_tweets.csv').sort_values('relevancy')
X = dataset.iloc[-100:, :-1].values
y = dataset.iloc[-100:, -1].values

# transform certain fields so that they are usable during training
for idx in range(X.shape[0]):
    readingLevel = X[idx, 64].split()[0][:-2]
    X[idx, 64] = readingLevel

# get useful fields from x (columns 19-30 and 53-69)
relevantStatistics = ['combined syllable count', 'combined lexicon count', 'combined sentence count', 'combined flesch reading ease score',
                      'combined flesch-kincaid grade level','combined fog scale','combined smog index', 'combined automated readability index',
                      'combined coleman-liau index', 'combined linsear write level','combined dale-chall readability score']
relevantIndices = []
for i in relevantStatistics:
    relevantIndices.append(np.where(dataset.columns.values == i)[0][0])

usefulX = X[:, np.r_[relevantIndices]]

# create testing and training datasets
X_train, X_test, y_train, y_test = train_test_split(usefulX, np.asarray(y, dtype=float), test_size=0.3)

# train regression model
clf = LinearRegression()

# train on minibatch
clf.fit(X_train, y_train)

# test trained model
y_pred = clf.predict(X_test)
print("\tPrediction: ", y_pred)
print("\tI Prediction: ",  np.rint(y_pred))
print("\tReal:       ", y_test)

MAE = metrics.mean_absolute_error(y_test, y_pred)
tn, fp, fn, tp = confusion_matrix(y_test, np.rint(y_pred)).ravel()
print("\t%.5f" % MAE)
print("\tType I Error: %d" % fp)
print("\tType II Error: %d" % fn)

# save regression model to artifacts folder
with open('../artifacts/relevancyModel.sav', 'wb') as outfile:
    pickle.dump(clf, outfile)