document.querySelectorAll('input[data-mask]').forEach(input => {
    input.addEventListener('input', function(e) {
        let v = e.target.value.replace(/\D/g, '');
        if (e.target.dataset.mask === 'cnpj') {
            v = v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        if (e.target.dataset.mask === 'cep') {
            v = v.replace(/^(\d{5})(\d{3})/, '$1-$2');
        }
        if (e.target.dataset.mask === 'telefone') {
            if (v.length <= 10) {
                v = v.replace(/^(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            } else {
                v = v.replace(/^(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            }
        }
        e.target.value = v;
    });
});