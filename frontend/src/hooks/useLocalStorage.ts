/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useRef } from 'react';

function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  // Use a ref to store initialValue to avoid effect re-running if initialValue reference changes
  // but we really only care about key changes.
  const initialValueRef = useRef(initialValue);
  
  // Update ref if initialValue changes, but this won't trigger the effect below
  useEffect(() => {
    initialValueRef.current = initialValue;
  }, [initialValue]);

  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  // If key changes, update the stored value from local storage
  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (item) {
          setStoredValue(JSON.parse(item));
      } else {
          setStoredValue(initialValueRef.current);
      }
    } catch (error) {
      console.error(error);
      setStoredValue(initialValueRef.current);
    }
  }, [key]);

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      setStoredValue((prevStoredValue) => {
        const valueToStore = value instanceof Function ? value(prevStoredValue) : value;
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        return valueToStore;
      });
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue];
}

export default useLocalStorage;
