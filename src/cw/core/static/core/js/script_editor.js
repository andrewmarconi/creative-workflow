/**
 * Alpine.js component for the TV Spot Script structured editor.
 * Manages script metadata and script_rows array following tvspot.schema.json.
 */
function scriptEditor(initialScript, schema) {
  return {
    script: initialScript && Object.keys(initialScript).length > 0
      ? {
          client_name: initialScript.client_name || "",
          brand_name: initialScript.brand_name || "",
          script_title: initialScript.script_title || "",
          total_runtime_seconds: initialScript.total_runtime_seconds || 0,
          language: initialScript.language || "",
          job_id: initialScript.job_id || "",
          notes: initialScript.notes || "",
        }
      : {
          client_name: "",
          brand_name: "",
          script_title: "",
          total_runtime_seconds: 0,
          language: "",
          job_id: "",
          notes: "",
        },

    scriptRows: initialScript && initialScript.script_rows && initialScript.script_rows.length > 0
      ? initialScript.script_rows.map((row) => ({
          shot_number: row.shot_number || "",
          timecode_start: row.timecode_start || "",
          duration_seconds: row.duration_seconds || 0,
          visual_text: row.visual_text || "",
          audio_text: row.audio_text || "",
        }))
      : [],

    schema: schema,
    validationError: null,

    addRow() {
      const nextShotNumber = String(this.scriptRows.length + 1).padStart(2, "0");
      this.scriptRows.push({
        shot_number: nextShotNumber,
        timecode_start: "00:00:00:00",
        duration_seconds: 0,
        visual_text: "",
        audio_text: "",
      });
    },

    removeRow(index) {
      this.scriptRows.splice(index, 1);
      // Renumber shots
      this.scriptRows.forEach((row, idx) => {
        row.shot_number = String(idx + 1).padStart(2, "0");
      });
    },

    validateScript() {
      this.validationError = null;

      // Basic validation
      if (!this.script.client_name.trim()) {
        this.validationError = "Client name is required";
        return false;
      }
      if (!this.script.brand_name.trim()) {
        this.validationError = "Brand name is required";
        return false;
      }
      if (!this.script.script_title.trim()) {
        this.validationError = "Script title is required";
        return false;
      }
      if (!this.script.total_runtime_seconds || this.script.total_runtime_seconds <= 0) {
        this.validationError = "Total runtime must be greater than 0";
        return false;
      }
      if (!this.script.language.trim()) {
        this.validationError = "Language is required";
        return false;
      }
      if (this.scriptRows.length === 0) {
        this.validationError = "At least one script row is required";
        return false;
      }

      // Validate each row
      for (let i = 0; i < this.scriptRows.length; i++) {
        const row = this.scriptRows[i];
        if (!row.shot_number.trim()) {
          this.validationError = `Shot ${i + 1}: Shot number is required`;
          return false;
        }
        if (!row.timecode_start.trim()) {
          this.validationError = `Shot ${i + 1}: Timecode start is required`;
          return false;
        }
        if (!row.timecode_start.match(/^\d{2}:\d{2}:\d{2}:\d{2}$/)) {
          this.validationError = `Shot ${i + 1}: Timecode must be in HH:MM:SS:FF format`;
          return false;
        }
        if (!row.duration_seconds || row.duration_seconds <= 0) {
          this.validationError = `Shot ${i + 1}: Duration must be greater than 0`;
          return false;
        }
        if (!row.visual_text.trim()) {
          this.validationError = `Shot ${i + 1}: Visual description is required`;
          return false;
        }
        if (!row.audio_text.trim()) {
          this.validationError = `Shot ${i + 1}: Audio description is required`;
          return false;
        }
      }

      // All validations passed
      return true;
    },

    syncToField() {
      // Build complete script object
      const fullScript = {
        client_name: this.script.client_name,
        brand_name: this.script.brand_name,
        script_title: this.script.script_title,
        total_runtime_seconds: this.script.total_runtime_seconds,
        language: this.script.language,
        script_rows: this.scriptRows.map((row) => ({
          shot_number: row.shot_number,
          timecode_start: row.timecode_start,
          duration_seconds: row.duration_seconds,
          visual_text: row.visual_text,
          audio_text: row.audio_text,
        })),
      };

      // Add optional fields if present
      if (this.script.job_id.trim()) {
        fullScript.job_id = this.script.job_id;
      }
      if (this.script.notes.trim()) {
        fullScript.notes = this.script.notes;
      }

      this.$refs.jsonField.value = JSON.stringify(fullScript, null, 2);
    },
  };
}
