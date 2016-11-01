from features.feature_params import FeatureParameters
from parsing import config
from parsing.action import Actions
from parsing.config import Config


class Model(object):
    def __init__(self, model_type, filename, labels=None, feature_extractor=None, model=None):
        self._update_only_on_error = None
        self.model_type = model_type
        self.filename = filename
        if feature_extractor is not None and model is not None:
            self.feature_extractor = feature_extractor
            self.model = model
            return

        if model_type == config.SPARSE_PERCEPTRON:
            from classifiers.sparse_perceptron import SparsePerceptron
            from features.sparse_features import SparseFeatureExtractor
            self.feature_extractor = SparseFeatureExtractor()
            self.model = SparsePerceptron(filename, labels, min_update=Config().args.minupdate)
        elif model_type == config.DENSE_PERCEPTRON:
            from features.embedding import FeatureEmbedding
            from classifiers.dense_perceptron import DensePerceptron
            self.feature_extractor = self.dense_features_wrapper(FeatureEmbedding)
            self.model = DensePerceptron(filename, labels, num_features=self.feature_extractor.num_features())
        elif model_type == config.FEEDFORWARD_NN:
            from features.enumerator import FeatureEnumerator
            from nn.feedforward import FeedforwardNeuralNetwork
            self.feature_extractor = self.dense_features_wrapper(FeatureEnumerator)
            self.model = FeedforwardNeuralNetwork(filename, labels, input_params=self.feature_extractor.params,
                                                  layers=Config().args.layers,
                                                  layer_dim=Config().args.layerdim,
                                                  activation=Config().args.activation,
                                                  normalize=Config().args.normalize,
                                                  init=Config().args.init,
                                                  max_num_labels=Config().args.maxlabels,
                                                  batch_size=Config().args.batchsize,
                                                  minibatch_size=Config().args.minibatchsize,
                                                  nb_epochs=Config().args.nbepochs,
                                                  dropout=Config().args.dropout,
                                                  optimizer=Config().args.optimizer,
                                                  loss=Config().args.loss,
                                                  )
        else:
            raise ValueError("Invalid model type: '%s'" % model_type)

    @staticmethod
    def dense_features_wrapper(wrapper):
        from features.dense_features import DenseFeatureExtractor
        params = [
            FeatureParameters("w", Config().args.wordvectors, Config().args.maxwords, Config().args.worddropout),
            FeatureParameters("t", Config().args.tagdim, Config().args.maxtags),
            FeatureParameters("e", Config().args.labeldim, Config().args.maxedgelabels),
            FeatureParameters("p", Config().args.punctdim, Config().args.maxpuncts),
            FeatureParameters("x", Config().args.gapdim, Config().args.maxgaps),
            FeatureParameters("A", Config().args.actiondim, Config().args.maxactions),
        ]
        return wrapper(DenseFeatureExtractor(), params)

    def extract_features(self, *args, **kwargs):
        return self.feature_extractor.extract_features(*args, **kwargs)

    def score(self, *args, **kwargs):
        return self.model.score(*args, **kwargs)

    def update(self, *args, **kwargs):
        self.model.update(*args, **kwargs)

    def finish(self, train):
        self.model.finish(train)

    def advance(self):
        self.model.advance()

    @property
    def update_only_on_error(self):
        if self._update_only_on_error is None:
            self._update_only_on_error = self.model_type in (config.SPARSE_PERCEPTRON, config.DENSE_PERCEPTRON)
        return self._update_only_on_error

    def finalize(self, *args, **kwargs):
        return Model(model_type=self.model_type,
                     filename=self.filename,
                     feature_extractor=self.feature_extractor.finalize(*args, **kwargs),
                     model=self.model.finalize(*args, **kwargs))

    def save(self):
        if self.filename is not None:
            try:
                self.feature_extractor.save(self.filename)
                self.model.save()
            except Exception as e:
                raise IOError("Failed saving model to '%s'" % self.filename, e)

    def load(self):
        if self.filename is not None:
            try:
                self.feature_extractor.load(self.filename)
                self.model.load()
                Actions().all = self.model.labels
            except Exception as e:
                raise IOError("Failed loading model from '%s'" % self.filename, e)
