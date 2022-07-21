import copy
from typing import Type

import torch
from river import base

from river_torch.base import DeepEstimator, RollingDeepEstimator
from river_torch.utils.river_compat import dict2tensor, list2tensor, scalar2tensor


class Regressor(DeepEstimator, base.Regressor):
    """Compatibility layer from PyTorch to River for regression.

    Parameters
    ----------
    build_fn
    loss_fn
    optimizer_fn
    batch_size

    Examples
    --------

    >>> from river import datasets
    >>> from river import evaluate
    >>> from river import metrics
    >>> from river import preprocessing
    >>> from river_torch.regression import Regressor
    >>> import torch
    >>> from torch import nn
    >>> from torch import optim

    >>> _ = torch.manual_seed(0)

    >>> dataset = datasets.TrumpApproval()
    >>> def build_torch_mlp(n_features):
    ...     net = nn.Sequential(
    ...         nn.Linear(n_features, 5),
    ...         nn.ReLU(),
    ...         nn.Linear(5, 1)
    ...     )
    ...     return net
    ...


    >>> model = (
    ...     preprocessing.StandardScaler() |
    ...     Regressor(
    ...         build_fn=build_torch_mlp,
    ...         loss_fn='mse',
    ...         optimizer_fn=torch.optim.SGD,
    ...         batch_size=2
    ...     )
    ... )
    >>> metric = metrics.MAE()

    >>> evaluate.progressive_val_score(dataset, model, metric).get()
    1.3456

    """

    def __init__(
        self,
        build_fn,
        optimizer_fn,
        loss_fn="mse",
        device="cpu",
        learning_rate=1e-3,
        **net_params
    ):
        super().__init__(
            build_fn=build_fn,
            loss_fn=loss_fn,
            device=device,
            optimizer_fn=optimizer_fn,
            learning_rate=learning_rate,
            **net_params
        )

    def learn_one(self, x: dict, y: base.typing.RegTarget):
        if self.net is None:
            self._init_net(len(x))
        x = dict2tensor(x, self.device)
        y = scalar2tensor(y, device=self.device)
        self.net.train()
        self._learn_one(x, y)
        return self

    def _learn_one(self, x: torch.TensorType, y: torch.TensorType):
        self.optimizer.zero_grad()
        y_pred = self.net(x)
        loss = self.loss_fn(y_pred, y)
        loss.backward()
        self.optimizer.step()

    def predict_one(self, x: dict) -> base.typing.RegTarget:
        if self.net is None:
            self._init_net(len(x))
        x = dict2tensor(x, self.device)
        self.net.eval()
        return self.net(x).item()


class RollingRegressor(RollingDeepEstimator, base.Regressor):
    """
    A Rolling Window PyTorch to River Regressor
    Parameters
    ----------
    build_fn
    loss_fn
    optimizer_fn
    window_size
    learning_rate
    net_params
    """

    def predict_one(self, x: dict):
        if self.net is None:
            self._init_net(len(x))
        if len(self._x_window) == self.window_size:

            if self.append_predict:
                self._x_window.append(list(x.values()))
                x = list2tensor(self._x_window, self.device)
            else:
                x = copy.deepcopy(self._x_window)
                x.append(list(x.values()))
                x = list2tensor(x, self.device)
            self.net.eval()
            return self.net(x).item()
        else:
            return 0.0

    def learn_one(self, x: dict, y: base.typing.RegTarget):
        if self.net is None:
            self._init_net(len(x))

        self._x_window.append(list(x.values()))
        if len(self._x_window) == self.window_size:
            x = list2tensor(self._x_window, device=self.device)
            y = scalar2tensor(y, device=self.device)
            self.net.train()
            self._learn_window(x, y)

        return self

    def _learn_window(self, x: torch.TensorType, y: torch.TensorType):
        self.optimizer.zero_grad()
        y_pred = self.net(x)
        loss = self.loss_fn(y_pred, y)
        loss.backward()
        self.optimizer.step()
