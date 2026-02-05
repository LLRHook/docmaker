declare global {
  interface Window {
    pyloid: {
      DocmakerAPI: {
        scan_project(path: string): Promise<string>;
        generate_docs(options: string): Promise<string>;
        get_graph_data(): Promise<string>;
        parse_only(path: string): Promise<string>;
        open_file(path: string, line: number): Promise<string>;
        get_project_info(): Promise<string>;
        get_class_details(classFqn: string): Promise<string>;
        get_endpoint_details(endpointKey: string): Promise<string>;
      };
    };
  }
}

export {};
