from utils import TrainClock
import os
import torch
import torch.optim as optim
import torch.nn as nn
from abc import abstractmethod
import numpy as np
from networks import get_network


def get_agent(config):
    return MyAgent(config)


class BaseAgent(object):
    """Base trainer that provides commom training behavior. 
        All trainer should be subclass of this class.
    """
    def __init__(self, config):
        self.log_dir = config.log_dir
        self.model_dir = config.model_dir
        self.clock = TrainClock()
        self.device = config.device
        self.batch_size = config.batch_size

        # build network
        self.net = self.build_net(config).cuda()

        # set loss function
        self.set_loss_function()

        # set optimizer
        self.set_optimizer(config)

    @abstractmethod
    def build_net(self, config):
        raise NotImplementedError

    def set_loss_function(self):
        """set loss function used in training"""
        self.criterion = nn.MSELoss().cuda()

    def set_optimizer(self, config):
        """set optimizer and lr scheduler used in training"""
        self.optimizer = optim.Adam(self.net.parameters(), config.lr)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, config.lr_step_size)

    def save_ckpt(self, name=None):
        """save checkpoint during training for future restore"""
        if name is None:
            save_path = os.path.join(self.model_dir, "ckpt_epoch{}.pth".format(self.clock.epoch))
        else:
            save_path = os.path.join(self.model_dir, name)
        if isinstance(self.net, nn.DataParallel):
            torch.save({
                'clock': self.clock.make_checkpoint(),
                'model_state_dict': self.net.module.cpu().state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'scheduler_state_dict': self.scheduler.state_dict(),
            }, save_path)
        else:
            torch.save({
                'clock': self.clock.make_checkpoint(),
                'model_state_dict': self.net.cpu().state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'scheduler_state_dict': self.scheduler.state_dict(),
            }, save_path)
        self.net.cuda()

    def load_ckpt(self, path=None):
        """load checkpoint from saved checkpoint"""
        if path is not None:
            load_path = path
        else:
            load_path = os.path.join(self.model_dir, "latest.pth.tar")
        checkpoint = torch.load(load_path)
        if isinstance(self.net, nn.DataParallel):
            self.net.module.load_state_dict(checkpoint['model_state_dict'])
        else:
            self.net.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.clock.restore_checkpoint(checkpoint['clock'])

    @abstractmethod
    def forward(self, data):
        pass

    def update_network(self, loss_dict):
        """update network by back propagation"""
        loss = sum(loss_dict.values())
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def update_learning_rate(self):
        self.scheduler.step(self.clock.epoch)

    def train_func(self, data):
        """one step of training"""
        self.net.train()

        outputs, losses = self.forward(data)

        self.update_network(losses)

        return outputs, losses

    def val_func(self, data):
        """one step of validation"""
        self.net.eval()

        with torch.no_grad():
            outputs, losses = self.forward(data)

        return outputs, losses

    def visualize_batch(self, data, tb, **kwargs):
        """write visualization results to tensorboard writer"""
        raise NotImplementedError


class MyAgent(BaseAgent):
    def build_net(self, config):
        # customize your build_net function
        # should return the built network
        return get_network(config)

    def forward(self, data):
        # customize your forward function
        # should return the network outputs and losses

        # input_vox3d = data['vox3d'].to(self.device)
        # target_vox3d = input_vox3d.clone().detach()

        # output_vox3d = self.net(input_vox3d)

        # loss = self.criterion(output_vox3d, target_vox3d)
        # return output_vox3d, {"mse": loss}
        pass