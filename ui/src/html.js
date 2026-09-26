/**
 * ui/src/html.js
 * ==============
 * Re-exports React 18, ReactDOM, and HTM for JSX-like syntax in native browser ES Modules.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import htm from 'htm';

export const html = htm.bind(React.createElement);
export { React, ReactDOM };
export const {
  useState,
  useEffect,
  useContext,
  useRef,
  useCallback,
  useMemo,
  createContext
} = React;
