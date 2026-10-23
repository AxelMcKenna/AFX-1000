"""Small complex linear solvers, independent of any board contract."""


def linear_solve(matrix, rhs):
    """Complex Gaussian elimination with partial pivoting, no numeric package."""
    n = len(rhs)
    for i in range(n):
        pivot = max(range(i, n), key=lambda j: abs(matrix[j][i]))
        if abs(matrix[pivot][i]) < 1e-14:
            raise ValueError("Singular circuit")
        matrix[i], matrix[pivot] = matrix[pivot], matrix[i]
        rhs[i], rhs[pivot] = rhs[pivot], rhs[i]
        divisor = matrix[i][i]
        for k in range(i, n):
            matrix[i][k] /= divisor
        rhs[i] /= divisor
        for j in range(i + 1, n):
            factor = matrix[j][i]
            for k in range(i, n):
                matrix[j][k] -= factor * matrix[i][k]
            rhs[j] -= factor * rhs[i]
    result = [0j] * n
    for i in reversed(range(n)):
        result[i] = rhs[i] - sum(matrix[i][k] * result[k] for k in range(i + 1, n))
    return result


class LU:
    def __init__(self, m):
        self.m = [row[:] for row in m]
        self.piv = list(range(len(m)))
        n = len(m)
        for k in range(n):
            pivot = max(range(k, n), key=lambda i: abs(self.m[i][k]))
            self.m[k], self.m[pivot] = self.m[pivot], self.m[k]
            self.piv[k], self.piv[pivot] = self.piv[pivot], self.piv[k]
            if abs(self.m[k][k]) < 1e-18:
                raise ValueError("Singular circuit")
            for i in range(k + 1, n):
                self.m[i][k] /= self.m[k][k]
                factor = self.m[i][k]
                for j in range(k + 1, n):
                    self.m[i][j] -= factor * self.m[k][j]

    def solve(self, b):
        n = len(b)
        y = [0j] * n
        x = [0j] * n
        for i in range(n):
            y[i] = b[self.piv[i]] - sum(self.m[i][j] * y[j] for j in range(i))
        for i in reversed(range(n)):
            x[i] = (y[i] - sum(self.m[i][j] * x[j] for j in range(i + 1, n))) / self.m[i][i]
        return x
