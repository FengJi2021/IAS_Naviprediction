from torch.nn import Module
from torch.nn import Conv2d
from torch.nn import Linear
from torch.nn import MaxPool2d
from torch.nn import ReLU
from torch.nn import LogSoftmax
from torch import flatten
import torch
from torch.nn import MSELoss



class cnn_basic(Module):
    def __init__(self, numChannels,f2_dim, conv1_dim=40, conv2_dim=20, f1_dim=50) -> None:
        super().__init__()
        self.conv1 = Conv2d(in_channels=numChannels, out_channels=conv1_dim,
			kernel_size=(5, 5))
        self.relu1 = ReLU()
        self.maxpool_1 = MaxPool2d(kernel_size=(2, 2), stride=(2, 2))
        
        self.conv2 = Conv2d(in_channels=conv1_dim, out_channels=conv2_dim, kernel_size=(5, 5))
        self.relu2 = ReLU()
        self.maxpool_2 = MaxPool2d(kernel_size=(2, 2), stride=(2, 2))
        
        self.input_dim = None
        self.fc1 = Linear(in_features=self.input_dim, out_features=f1_dim)
        self.relu3 = ReLU()
        
        self.fc2 = Linear(in_features=f1_dim, out_features=f2_dim)
        self.logSoftmax = LogSoftmax(dim=1)
        
        self.loss = MSELoss()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.maxpool_1(x)
        x = self.conv2(x)
        x = self.relu2(x)
        x = self.maxpool_2(x)
        # fc 
        x = flatten(x, 1)
        output = self.logSoftmax(x)
        
        return output


##cli
#import argparse
#ap = argparse.ArgumentParser()
#ap.add_argument("-m", "--model", type=str, required=True)
#ap.add_argument("-p", "--plot", type=str, required=True)
#args = vars(ap.parse_args())





        
  
        
        
        
  
  