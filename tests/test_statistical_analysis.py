"""statistical_analysis.py 单元测试"""
import pytest
import numpy as np
from statistical_analysis import StandardScaler, PCA, LinearRegression, r2_score


class TestStandardScaler:
    def test_fit_transform_shape(self):
        data = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
        scaler = StandardScaler()
        result = scaler.fit_transform(data)
        assert result.shape == data.shape

    def test_mean_zero(self):
        data = np.random.randn(100, 3)
        scaler = StandardScaler()
        result = scaler.fit_transform(data)
        means = result.mean(axis=0)
        assert np.allclose(means, 0, atol=1e-10)

    def test_std_one(self):
        data = np.random.randn(100, 3)
        scaler = StandardScaler()
        result = scaler.fit_transform(data)
        stds = result.std(axis=0)
        assert np.allclose(stds, 1, atol=1e-10)

    def test_constant_column(self):
        data = np.array([[1, 5], [2, 5], [3, 5]], dtype=float)
        scaler = StandardScaler()
        result = scaler.fit_transform(data)
        assert np.allclose(result[:, 1], 0)


class TestPCA:
    def test_output_shape(self):
        data = np.random.randn(50, 5)
        pca = PCA(n_components=2)
        result = pca.fit_transform(data)
        assert result.shape == (50, 2)

    def test_explained_variance_ratio_sum(self):
        data = np.random.randn(50, 5)
        pca = PCA(n_components=3)
        pca.fit_transform(data)
        total = sum(pca.explained_variance_ratio_)
        assert 0.9 < total <= 1.0

    def test_components_shape(self):
        data = np.random.randn(50, 5)
        pca = PCA(n_components=2)
        pca.fit_transform(data)
        assert pca.components_.shape == (2, 5)

    def test_single_component(self):
        data = np.random.randn(20, 3)
        pca = PCA(n_components=1)
        result = pca.fit_transform(data)
        assert result.shape == (20, 1)


class TestLinearRegression:
    def test_perfect_fit(self):
        X = np.array([[1], [2], [3], [4], [5]], dtype=float)
        y = np.array([2, 4, 6, 8, 10], dtype=float)
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        assert np.allclose(pred, y, atol=1e-10)

    def test_coefficients(self):
        X = np.array([[1], [2], [3]], dtype=float)
        y = np.array([3, 5, 7], dtype=float)
        model = LinearRegression()
        model.fit(X, y)
        assert abs(model.coef_[0] - 2.0) < 1e-10
        assert abs(model.intercept_ - 1.0) < 1e-10

    def test_predict_shape(self):
        X = np.random.randn(20, 1)
        y = np.random.randn(20)
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        assert len(pred) == 20


class TestR2Score:
    def test_perfect(self):
        y = np.array([1, 2, 3, 4, 5], dtype=float)
        assert r2_score(y, y) == 1.0

    def test_mean_prediction(self):
        y = np.array([1, 2, 3, 4, 5], dtype=float)
        pred = np.full_like(y, y.mean())
        assert abs(r2_score(y, pred)) < 1e-10
