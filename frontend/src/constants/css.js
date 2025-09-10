// CSS properties and effects
export const css = {
  // Box shadows
  shadows: {
    none: "none",
    sm: "0 1px 2px rgba(0, 0, 0, 0.05)",
    base: "0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)",
    md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    xxl: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
    inner: "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",
  },

  // Transitions
  transitions: {
    none: "none",
    all: "all 0.15s ease-in-out",
    colors:
      "color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out",
    opacity: "opacity 0.15s ease-in-out",
    transform: "transform 0.15s ease-in-out",
    fast: "all 0.1s ease-in-out",
    slow: "all 0.3s ease-in-out",
  },

  // Z-index layers
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },

  // Border styles
  borders: {
    none: "none",
    solid: "1px solid",
    dashed: "1px dashed",
    dotted: "1px dotted",
    double: "3px double",
  },

  // Opacity values
  opacity: {
    0: "0",
    25: "0.25",
    50: "0.5",
    75: "0.75",
    100: "1",
  },

  // Cursor styles
  cursors: {
    auto: "auto",
    default: "default",
    pointer: "pointer",
    wait: "wait",
    text: "text",
    move: "move",
    help: "help",
    notAllowed: "not-allowed",
  },

  // Display properties
  display: {
    block: "block",
    inline: "inline",
    inlineBlock: "inline-block",
    flex: "flex",
    inlineFlex: "inline-flex",
    grid: "grid",
    none: "none",
  },

  // Position values
  position: {
    static: "static",
    relative: "relative",
    absolute: "absolute",
    fixed: "fixed",
    sticky: "sticky",
  },

  // Text align
  textAlign: {
    left: "left",
    center: "center",
    right: "right",
    justify: "justify",
  },

  // Flex properties
  flex: {
    direction: {
      row: "row",
      column: "column",
      rowReverse: "row-reverse",
      columnReverse: "column-reverse",
    },
    wrap: {
      nowrap: "nowrap",
      wrap: "wrap",
      wrapReverse: "wrap-reverse",
    },
    justify: {
      start: "flex-start",
      end: "flex-end",
      center: "center",
      between: "space-between",
      around: "space-around",
      evenly: "space-evenly",
    },
    align: {
      start: "flex-start",
      end: "flex-end",
      center: "center",
      baseline: "baseline",
      stretch: "stretch",
    },
  },
};
