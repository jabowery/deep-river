import warnings

from river import metrics, datasets, compose, preprocessing
from river_torch.classification import Classifier
from torch import nn

if __name__ == '__main__':
    dataset = datasets.Keystroke()
    metric = metrics.Accuracy()

    class MyModule(nn.Module):
        def __init__(self, n_features):
            super(MyModule, self).__init__()
            self.dense0 = nn.Linear(n_features,5)
            self.nonlin = nn.ReLU()
            self.dense1 = nn.Linear(5, 2)
            self.softmax = nn.Softmax(dim=-1)

        def forward(self, X, **kwargs):
            X = self.nonlin(self.dense0(X))
            X = self.nonlin(self.dense1(X))
            X = self.softmax(X)
            return X

    model_pipeline = compose.Pipeline(
        preprocessing.StandardScaler,
        Classifier(module=MyModule,
                   loss_fn="binary_cross_entropy",
                   optimizer_fn='adam',
                   is_class_incremental=True)
    )

    for x, y in dataset.take(10000):
        y_pred = model_pipeline.predict_one(x)  # make a prediction
        metric = metric.update(y, y_pred)  # update the metric
        model_pipeline = model_pipeline.learn_one(x, y)  # make the model learn
    print(f'Accuracy: {metric.get()}')