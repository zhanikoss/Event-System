from typing import Generic, TypeVar, Callable, Union
from dataclasses import dataclass

T = TypeVar('T')
U = TypeVar('U')
E = TypeVar('E')

# Maybe monad (Option type)
class Maybe(Generic[T]):
    @staticmethod
    def just(value: T) -> 'Maybe[T]':
        return Just(value)
    
    @staticmethod
    def nothing() -> 'Maybe[T]':
        return Nothing()
    
    def map(self, func: Callable[[T], U]) -> 'Maybe[U]':
        raise NotImplementedError
    
    def bind(self, func: Callable[[T], 'Maybe[U]']) -> 'Maybe[U]':
        raise NotImplementedError
    
    def get_or_else(self, default: T) -> T:
        raise NotImplementedError

@dataclass(frozen=True)
class Just(Maybe[T]):
    value: T
    
    def map(self, func: Callable[[T], U]) -> Maybe[U]:
        return Just(func(self.value))
    
    def bind(self, func: Callable[[T], Maybe[U]]) -> Maybe[U]:
        return func(self.value)
    
    def get_or_else(self, default: T) -> T:
        return self.value

@dataclass(frozen=True)
class Nothing(Maybe[T]):
    def map(self, func: Callable[[T], U]) -> Maybe[U]:
        return Nothing()
    
    def bind(self, func: Callable[[T], Maybe[U]]) -> Maybe[U]:
        return Nothing()
    
    def get_or_else(self, default: T) -> T:
        return default

# Either monad (Result type)
class Either(Generic[E, T]):
    @staticmethod
    def right(value: T) -> 'Either[E, T]':
        return Right(value)
    
    @staticmethod
    def left(error: E) -> 'Either[E, T]':
        return Left(error)
    
    def map(self, func: Callable[[T], U]) -> 'Either[E, U]':
        raise NotImplementedError
    
    def bind(self, func: Callable[[T], 'Either[E, U]']) -> 'Either[E, U]':
        raise NotImplementedError
    
    def get_or_else(self, default: T) -> T:
        raise NotImplementedError

@dataclass(frozen=True)
class Right(Either[E, T]):
    value: T
    
    def map(self, func: Callable[[T], U]) -> Either[E, U]:
        return Right(func(self.value))
    
    def bind(self, func: Callable[[T], Either[E, U]]) -> Either[E, U]:
        return func(self.value)
    
    def get_or_else(self, default: T) -> T:
        return self.value

@dataclass(frozen=True)
class Left(Either[E, T]):
    error: E
    
    def map(self, func: Callable[[T], U]) -> Either[E, U]:
        return Left(self.error)
    
    def bind(self, func: Callable[[T], Either[E, U]]) -> Either[E, U]:
        return Left(self.error)
    
    def get_or_else(self, default: T) -> T:
        return default