/**
 * ui/src/main.js
 * ==============
 * Entry point mounting the React 18 application onto #root.
 */

import { html, ReactDOM } from './html.js';
import { AuthProvider } from './context/AuthContext.js';
import { PipelineProvider } from './context/PipelineContext.js';
import { App } from './App.js';
import { ErrorBoundary } from './components/ErrorBoundary.js';

const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(html`
    <${ErrorBoundary}>
      <${AuthProvider}>
        <${PipelineProvider}>
          <${App} />
        <//>
      <//>
    <//>
  `);
}
