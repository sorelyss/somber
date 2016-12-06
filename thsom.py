import numpy as np
import logging
import time
import cProfile

from som import Som
from progressbar import progressbar

logging.basicConfig(level=logging.INFO)


class THSom(Som):

    def __init__(self, width, height, dim, learning_rates, beta):

        super().__init__(width, height, dim, learning_rates)
        self.temporal_weights = np.zeros((self.map_dim, self.map_dim))
        self.const_dim = np.sqrt(self.data_dim)
        self.beta = beta

    def epoch_step(self, X, map_radius, learning_rate, batch_size):
        """
        A single example.

        :param X: a numpy array of examples
        :param map_radius: The radius at the current epoch, given the learning rate and map size
        :param learning_rate: The learning rate.
        :param batch_size: The batch size
        :return: The best matching unit
        """

        # Calc once per epoch
        self.grid, self.grid_distances = self._distance_grid(map_radius)

        learning_rate = learning_rate[0]

        # One radius per epoch
        map_radius_squared = (2 * map_radius) ** 2

        # One cache per epoch
        cache = {}

        # One accumulator per epoch
        # bmus = np.zeros((X.shape[0], X.shape[1]), dtype=np.int)
        all_distances = np.zeros((self.map_dim,))

        # Make a batch generator.
        accumulator = np.zeros_like(self.weights)
        temporal_accumulator = np.zeros_like(self.temporal_weights)
        num_updates = 0

        num_batches = np.ceil(len(X) / batch_size).astype(int)

        temporal_sum = self.temporal_weights.sum(axis=0)

        tempo = learning_rate * (self.temporal_weights + self.beta)
        mintempo = learning_rate * (1 - self.temporal_weights + self.beta)

        for index in progressbar(range(num_batches), idx_interval=1, mult=batch_size):

            # Select the current batch.
            current = X[index * batch_size: (index+1) * batch_size]

            # Initial previous activation
            prev_activations = np.zeros((current.shape[0], self.map_dim))

            prev_bmu = np.zeros((batch_size,), dtype=np.int)

            for idx in range(current.shape[1]):

                column = current[:, idx, :]

                influences = []

                # Get the indices of the Best Matching Unit, given the data.
                bmu_theta, prev_activations, spatial, temporal = self._get_bmus(column,
                                                                                y=prev_activations,
                                                                                temporal_sum=temporal_sum)

                for bmu in bmu_theta:

                    try:
                        influence_spatial = cache[bmu]
                    except KeyError:

                        x_, y_ = self._index_dict[bmu]
                        influence = self._calculate_influence(map_radius_squared, center_x=x_, center_y=y_)
                        influence *= learning_rate
                        influence_spatial = np.tile(influence, (self.data_dim, 1)).T
                        cache[bmu] = influence_spatial

                    influences.append(influence_spatial)

                influences = np.array(influences)

                spatial_update = self._update(spatial, influences).mean(axis=0)
                temporal_update = self._temporal_update(tempo, mintempo, prev_bmu=prev_bmu)

                accumulator += spatial_update
                temporal_accumulator += temporal_update
                num_updates += 1

                prev_bmu = bmu_theta

        self.weights += (accumulator / num_updates)
        self.temporal_weights += (temporal_accumulator / num_updates)

        self.weights = self.weights.clip(0.0, 1.0)
        self.temporal_weights = self.temporal_weights.clip(0.0, 1.0)

        return np.array(all_distances / num_updates)

    def _get_bmus(self, x, **kwargs):
        """
        Gets the best matching units, based on euclidean distance.

        :param x: The input vector
        :return: An integer, representing the index of the best matching unit.
        """

        y = kwargs['y']
        temporal_sum = kwargs['temporal_sum']

        spatial_differences = self._pseudo_distance(x, self.weights)

        temporal_differences = y * temporal_sum

        differences = (self.const_dim - np.sqrt(np.sum(np.square(spatial_differences), axis=2)) + temporal_differences)
        differences /= differences.max(axis=0)

        return np.argmax(differences, axis=1), differences, spatial_differences, temporal_differences

    @staticmethod
    def _temporal_update(tempo, mintempo, prev_bmu):
        """


        :param tempo:
        :param mintempo:
        :param prev_bmu:
        :return:
        """

        update = -tempo
        update[prev_bmu] += mintempo[prev_bmu]

        return update.T

    def predict(self, X):
        """
        Predicts node identity for input data.
        Similar to a clustering procedure.

        :param x: The input data.
        :return: A list of indices
        """

        # Start with a clean buffer.

        prev_activations = np.zeros((X.shape[0], self.map_dim))

        all_bmus = []
        temporal_sum = self.temporal_weights.sum(axis=0)

        for idx in range(X.shape[1]):

            column = X[:, idx, :]
            bmus, prev_activations, _, _ = self._get_bmus(column, y=prev_activations, temporal_sum=temporal_sum)

            all_bmus.append(bmus)

        return np.array(all_bmus).T

    def assign_exemplar(self, exemplars, names=()):

        exemplars = np.array(exemplars)
        distances = self._pseudo_distance(exemplars, self.weights)
        distances = np.sum(np.square(distances), axis=2)

        if not names:
            return distances.argmax(axis=0)
        else:
            return [names[x] for x in distances.argmax(axis=0)]

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    colors = np.array(
         [[1., 0., 1.],
          [0., 0., 0.],
          [0., 0., 1.],
          [0., 0., 0.5],
          [0.125, 0.529, 1.0],
          [0.33, 0.4, 0.67],
          [0.6, 0.5, 1.0],
          [0., 1., 0.],
          [1., 0., 0.],
          [0., 1., 1.],
          [1., 1., 0.],
          [1., 1., 1.],
          [.33, .33, .33],
          [.5, .5, .5],
          [.66, .66, .66]])

    data = np.tile(colors, (100, 1, 1))

    colorpicker = np.arange(len(colors))

    data = np.random.choice(colorpicker, size=(1000, 15))
    data = colors[data]

    s = THSom(30, 30, 3, [1.0], 0.01)
    start = time.time()
    cProfile.run("s.train(data, num_epochs=100, batch_size=100)")

    # bmu_history = np.array(bmu_history).T
    print("Took {0} seconds".format(time.time() - start))