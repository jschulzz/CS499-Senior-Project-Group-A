from sklearn.linear_model import LinearRegression
import pickle
import numpy as np
import os

class RelevancyModel():
    def __init__(self):
        try:
            self.model = pickle.load(open('../artifacts/relevancyModel.sav', 'rb'))
            self.loaded = True
        except Exception as e:
            print("Could not load relevancy model")
            print(e)
            self.loaded = False

    def getRelevancy(self, relevantStatValues):
        if self.loaded:
            return np.clip(self.model.predict(np.array(relevantStatValues).reshape(1, -1)), 0, 1)
        else:
            return 1
