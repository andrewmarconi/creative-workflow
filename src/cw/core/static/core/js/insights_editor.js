/**
 * Alpine.js component for the Insights structured editor.
 * Manages an array of {heading: string, points: string[]} objects.
 */
function insightsEditor(initialSections) {
  return {
    sections: initialSections && initialSections.length > 0 ? initialSections : [],

    addSection() {
      this.sections.push({ heading: "", points: [""] });
    },

    removeSection(index) {
      this.sections.splice(index, 1);
    },

    addPoint(sectionIndex) {
      this.sections[sectionIndex].points.push("");
    },

    removePoint(sectionIndex, pointIndex) {
      this.sections[sectionIndex].points.splice(pointIndex, 1);
    },

    syncToField() {
      const cleaned = this.sections
        .filter((s) => s.heading.trim() || s.points.some((p) => p.trim()))
        .map((s) => ({
          heading: s.heading,
          points: s.points.filter((p) => p.trim()),
        }));
      this.$refs.jsonField.value = JSON.stringify(cleaned, null, 2);
    },
  };
}
