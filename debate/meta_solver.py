from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Type, TypeVar

from debate.agent import Guideline

T = TypeVar('T', bound='MetaSolver')

class MetaSolver(ABC):
    """Abstract base class for Nash equilibrium solvers"""
    
    def __init__(self, 
                payoff_p_a: np.ndarray,
                payoff_p_b: Optional[np.ndarray] = None) -> None:
        """
        :param payoff_p_a: Payoff matrix for player 1 (m×n)
        :param payoff_p_b: Payoff matrix for player 2 (default is zero-sum with player 1)
        """
        self.payoff_p_a = payoff_p_a.astype(np.float64)
        self.payoff_p_b = (-payoff_p_a if payoff_p_b is None 
                        else payoff_p_b.astype(np.float64))
        self.m, self.n = payoff_p_a.shape  # Number of strategies for player 1 and player 2
        
    @classmethod
    def create(cls: Type[T], 
              guideline_pool_a: List[Guideline],
              similarity_matrix: Dict[Tuple[str, str], float],
              guideline_pool_b: List[Guideline]) -> T:
        """Factory method to create solver instance"""
        # Build payoff matrices
        payoff_p_a = np.zeros((len(guideline_pool_a), len(guideline_pool_b)), dtype=np.float64)
        payoff_p_b = np.zeros((len(guideline_pool_b), len(guideline_pool_a)), dtype=np.float64)
        for i, guideline_a in enumerate(guideline_pool_a):
            for j, guideline_b in enumerate(guideline_pool_b):
                acceptance = similarity_matrix[(guideline_a.content, guideline_b.content)]
                payoff_p_a[i, j] = acceptance + guideline_a.utility.consistency + guideline_a.utility.novelty
                payoff_p_b[j, i] = acceptance + guideline_b.utility.consistency + guideline_b.utility.novelty
        return cls(payoff_p_a, payoff_p_b)
    
    @abstractmethod
    def solve(self, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Abstract method: solve for equilibrium strategies"""

class MirrorDescentSolver(MetaSolver):
    """Mirror Descent algorithm implementation"""
    def __init__(self,
                payoff_p_a: np.ndarray,
                payoff_p_b: np.ndarray,
                gamma: float = 0.5) -> None:
        super().__init__(payoff_p_a, payoff_p_b)
        self.gamma = gamma  # Exploration parameter

    def _compute_gradients(self, 
                         a: np.ndarray, 
                         b: np.ndarray
                        ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute gradient vectors"""
        return self.payoff_p_a @ b, self.payoff_p_b.T @ a
    
    def _mirror_update(self, 
                      weights: np.ndarray, 
                      gradients: np.ndarray, 
                      eta: float
                     ) -> np.ndarray:
        """Mirror Descent update rule"""
        new_weights = weights * np.exp(eta * gradients)
        return new_weights / new_weights.sum()
    
    def apply_exploration(self, weights: np.ndarray) -> np.ndarray:
        """Apply γ-greedy exploration strategy"""
        num_strategies = len(weights)
        uniform = np.ones(num_strategies) / num_strategies  # Uniform distribution UNIF(n)
        return self.gamma * uniform + (1 - self.gamma) * weights

    def solve(self, 
             max_iter: int = 10000,
             eta: float = 0.1,
             tol: float = 1e-6,
             verbose: bool = False
            ) -> Tuple[np.ndarray, np.ndarray]:
        """Implement the specific solving logic"""
        # Initialize uniform strategies
        a = np.ones(self.m) / self.m
        b = np.ones(self.n) / self.n
        
        for t in range(max_iter):
            a_prev, b_prev = a.copy(), b.copy()
            
            # Compute gradients
            grad_a, grad_b = self._compute_gradients(a, b)
            
            # Update strategies
            a = self._mirror_update(a, grad_a, eta)
            b = self._mirror_update(b, grad_b, eta)
            
            # Check for convergence
            if (np.linalg.norm(a - a_prev) < tol and 
                np.linalg.norm(b - b_prev) < tol):
                if verbose:
                    print(f"Converged at iteration {t}")
                break
                
        return a, b

# ------------------- Usage Example -------------------
if __name__ == "__main__":
    # Payoff matrix for player 1 (5×5)
    payoff_p_a = np.array([
        [4, -1, 3, 0, 2],
        [-2, 5, 1, -3, 0],
        [1, 0, 6, -2, 4],
        [3, -4, 2, 7, -1],
        [0, 2, -1, 5, 3]
    ], dtype=np.float64)

    # Payoff matrix for player 2 (5×5)
    payoff_p_b = np.array([
        [2, 3, -1, 4, 0],
        [-3, 6, 2, 0, 1],
        [5, -2, 4, 1, -4],
        [1, 0, 3, 5, 2],
        [0, -1, 7, 2, 3]
    ], dtype=np.float64)

    # Create solver
    solver = MirrorDescentSolver(payoff_p_a, payoff_p_b)
    
    # Compute equilibrium
    a, b = solver.solve(max_iter=100000, eta=0.05, verbose=True)
    
    print("Player 1 equilibrium strategy:", np.round(a, 4))
    print("Player 2 equilibrium strategy:", np.round(b, 4))