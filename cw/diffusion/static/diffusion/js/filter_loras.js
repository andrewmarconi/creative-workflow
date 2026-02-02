document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    const modelField = document.getElementById('id_diffusion_model');
    const loraField = document.getElementById('id_lora_model');
    if (!modelField || !loraField) return;

    // Store all original LoRA options (skip the empty/None option at index 0)
    const emptyOption = loraField.options[0];
    const allOptions = Array.from(loraField.options).slice(1).map(function(opt) {
        return { value: opt.value, text: opt.text };
    });

    // The current value so we can preserve selection after filtering
    const currentLoraValue = loraField.value;

    function filterLoras() {
        const modelId = modelField.value;
        if (!modelId) {
            // No model selected — show all LoRAs
            rebuildOptions(allOptions, currentLoraValue);
            return;
        }

        fetch(window.__lora_compat_url__ + '?model_id=' + modelId)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var compatibleIds = data.lora_ids.map(String);
                var filtered = allOptions.filter(function(opt) {
                    return compatibleIds.indexOf(opt.value) !== -1;
                });
                rebuildOptions(filtered, currentLoraValue);
            });
    }

    function rebuildOptions(options, preserveValue) {
        loraField.innerHTML = '';
        loraField.appendChild(emptyOption.cloneNode(true));
        options.forEach(function(opt) {
            var el = document.createElement('option');
            el.value = opt.value;
            el.textContent = opt.text;
            if (opt.value === preserveValue) el.selected = true;
            loraField.appendChild(el);
        });
    }

    modelField.addEventListener('change', filterLoras);
    // Filter on page load
    filterLoras();
});
