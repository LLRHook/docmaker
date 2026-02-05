declare module "react-cytoscapejs" {
  import cytoscape from "cytoscape";
  import type { ComponentType, CSSProperties } from "react";

  interface CytoscapeComponentProps {
    elements: cytoscape.ElementDefinition[];
    stylesheet?: Array<{ selector: string; style: Record<string, unknown> }>;
    cy?: (cy: cytoscape.Core) => void;
    style?: CSSProperties;
    wheelSensitivity?: number;
    minZoom?: number;
    maxZoom?: number;
    zoom?: number;
    pan?: { x: number; y: number };
    autoungrabify?: boolean;
    autounselectify?: boolean;
    boxSelectionEnabled?: boolean;
    userZoomingEnabled?: boolean;
    userPanningEnabled?: boolean;
    selectionType?: "single" | "additive";
  }

  const CytoscapeComponent: ComponentType<CytoscapeComponentProps>;
  export default CytoscapeComponent;
}
