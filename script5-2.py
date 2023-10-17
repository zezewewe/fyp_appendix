#%%
import pickle
import pandas as pd 

import torch
from torch import nn

import numpy as np
import statistics

class MLP_Pos(nn.Module):
    '''
    Multilayer Perceptron for regression.
    '''
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(12, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            # nn.Linear(32, 64),
            # nn.ReLU(),
            nn.Linear(32, 2)
        )
    def forward(self, x): # forward pass
        return self.layers(x)
    
class MLP_Ori(nn.Module):
    '''
    Multilayer Perceptron for regression.
    '''
    def __init__(self):
        super().__init__()
        self.layers2 = nn.Sequential(
            nn.Linear(12, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 4)
        )
    def forward(self, x): # forward pass
        return self.layers2(x)


def data_inference(decoded_data_L,decoded_data_R):

    pos_preds=[]
    ori_preds=[]

    ############
    # METHOD ONE
    ############

    # From analysis, Expts 1a (6x2 known RSSI) and 1d (6x2+9x2 RSSI) are more reliable.
    # Linear Regression and K-Neighbors Regression for both expts 1a/d are more reliable

    average_L=[0.1*sum(decoded_data_L[i*10+1:(i+1)*10+1]) if i<14 else 0.1*sum(decoded_data_L[-10:]) for i in range(15)]
    average_R=[0.1*sum(decoded_data_R[i*10+1:(i+1)*10+1]) if i<14 else 0.1*sum(decoded_data_R[-10:]) for i in range(15)]

    # Note: investigate way to weight all the different [x,y] results.
    model_path='C:/Users/ngzew/fyp/scan/main/models/11Aug/method1models_septanddecdata.pkl'

    with open(model_path, 'rb') as file:
        models_import = pickle.load(file)

    #################################################
    # Input: [lists] decoded_data_L, decoded_data_R
    # Output: Position
    #################################################
    # ML
    pos_preds.append([i for i in models_import['1a']['LinearRegression'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]))[0]]) # High Confidence
    [i for i in models_import['1a']['KNeighborsRegression'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]))[0]]
    [i for i in models_import['1d']['LinearRegression'].predict(pd.DataFrame([average_L+average_R]))[0]]
    [i for i in models_import['1d']['KNeighborsRegression'].predict(pd.DataFrame([average_L+average_R]))[0]]

    # DL
    mlp=MLP_Pos()
    mlp.load_state_dict(torch.load('C:/Users/ngzew/fyp/scan/main/models/10Aug/method1mlp_septanddecdata.pkl'))
    pos_preds.append([i.item() for i in mlp(torch.Tensor(average_L[:6]+average_R[:6]).float())])

    #################################################
    # Input: [lists] decoded_data_L, decoded_data_R
    # Output: Orientation
    #################################################
    ori_preds.append(models_import['1b']['GaussianNB'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]))[0]) # Ranked #1
    ori_preds.append(models_import['1b']['ExtraTreesClassifier'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]))[0])
    models_import['1b']['BaggingClassifier'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]))[0]
    models_import['1b']['KNeighborsClassifier'].predict(pd.DataFrame([average_L[:6]+average_R[:6]]).values)[0] # Ranked #4 

    ori_preds.append(models_import['1h']['ExtraTreesClassifier'].predict(pd.DataFrame([average_L+average_R]))[0])
    ori_preds.append(models_import['1h']['GaussianNB'].predict(pd.DataFrame([average_L+average_R]))[0])
    models_import['1h']['BaggingClassifier'].predict(pd.DataFrame([average_L+average_R]))[0]
    models_import['1h']['KNeighborsClassifier'].predict(pd.DataFrame([average_L+average_R]).values)[0]

    # DL
    mlp=MLP_Ori()
    mlp.eval()
    mlp.load_state_dict(torch.load('C:/Users/ngzew/fyp/scan/main/models/10Aug/method1mlp-ori_septanddecdata100.pkl'))
    ori_preds.append(chr(torch.argmax(mlp(torch.Tensor([average_L[:6]+average_R[:6]]).float()),axis=1)+65)) # note additional dimension requierd here

    ############
    # METHOD TWO
    ############
    model_path='C:/Users/ngzew/fyp/scan/main/models/10Aug/method2models_septdecdata.pkl'
    with open(model_path, 'rb') as file:
        models_import = pickle.load(file)

    X_train, y_train=models_import['2a']
    # seems to have some issue: pos_preds.append([i for i in pd.DataFrame([average_L[:6]+average_R[:6]]).apply(lambda r:y_train.iloc[((r-X_train)**2).sum(axis=1).idxmin()],axis=1).iloc[0,:]])
    # this line works, but this method is not accurate in prediction, so remove pos_preds.append([i for i in y_train.iloc[np.argmin(np.sum((X_train - pd.DataFrame([average_L[1:7]+average_R[1:7]]).values)**2,axis=1))]])
    print(pos_preds,ori_preds)
    
    avg_pos = [statistics.mean(x) for x in zip(*pos_preds)]
    try:
        print(avg_pos, statistics.mode(ori_preds))
        return avg_pos, statistics.mode(ori_preds)
    except:
        print(avg_pos, statistics.mode(ori_preds))
        return avg_pos, ori_preds[0]

    # return [statistics.mean(x) for x in zip(*pos_preds)], statistics.mode(ori_preds)

# %%
##############
# METHOD THREE
##############
# model_path='C:/Users/ngzew/fyp/scan/main/models/10Aug/method3models_septdata.pkl'
# with open(model_path, 'rb') as file:
#   models_import = pickle.load(file)

# To implement algorithm again (this gives distances; Orientation one not accurate as well)


# %%
