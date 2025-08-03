import math
import random

class SimplexNoise:
    def __init__(self, seed=None):
        """Initialize Simplex noise generator with optional seed."""
        if seed is not None:
            random.seed(seed)
            
        # Gradient vectors for 2D
        self.grad2 = [
            (1, 1), (-1, 1), (1, -1), (-1, -1),
            (1, 0), (-1, 0), (1, 0), (-1, 0),
            (0, 1), (0, -1), (0, 1), (0, -1)
        ]
        
        # Permutation table
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm += self.perm

        # Skewing and unskewing factors for 2D
        self.F2 = 0.5 * (math.sqrt(3.0) - 1.0)
        self.G2 = (3.0 - math.sqrt(3.0)) / 6.0

    def dot2d(self, g, x, y):
        """Compute dot product in 2D."""
        return g[0] * x + g[1] * y

    def noise(self, xin, yin):
        """Generate 2D Simplex noise value."""
        # Skew input space to determine which simplex cell we're in
        s = (xin + yin) * self.F2
        i = math.floor(xin + s)
        j = math.floor(yin + s)
        
        # Unskew back to (x,y) space
        t = (i + j) * self.G2
        X0 = i - t
        Y0 = j - t
        x0 = xin - X0
        y0 = yin - Y0
        
        # Determine which simplex we are in
        i1, j1 = 0, 0
        if x0 > y0:
            i1 = 1
        else:
            j1 = 1
            
        # Offsets for corners
        x1 = x0 - i1 + self.G2
        y1 = y0 - j1 + self.G2
        x2 = x0 - 1.0 + 2.0 * self.G2
        y2 = y0 - 1.0 + 2.0 * self.G2
        
        # Work out the hashed gradient indices
        ii = int(i) & 255
        jj = int(j) & 255
        gi0 = self.perm[(ii + self.perm[jj]) & 255] % 12
        gi1 = self.perm[(ii + i1 + self.perm[jj + j1]) & 255] % 12
        gi2 = self.perm[(ii + 1 + self.perm[jj + 1]) & 255] % 12
        
        # Calculate contribution from three corners
        n0, n1, n2 = 0.0, 0.0, 0.0
        
        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0:
            t0 *= t0
            n0 = t0 * t0 * self.dot2d(self.grad2[gi0], x0, y0)
            
        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0:
            t1 *= t1
            n1 = t1 * t1 * self.dot2d(self.grad2[gi1], x1, y1)
            
        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0:
            t2 *= t2
            n2 = t2 * t2 * self.dot2d(self.grad2[gi2], x2, y2)
        
        # Add contributions from each corner to get the final noise value
        # The result is scaled to return values in the interval [-1,1]
        return 70.0 * (n0 + n1 + n2)

    def normalized_noise(self, x, y):
        """Generate noise value normalized to [0,1] range."""
        return (self.noise(x, y) + 1) / 2 