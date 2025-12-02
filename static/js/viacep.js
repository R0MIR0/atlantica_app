// static/js/viacep.js
document.addEventListener('DOMContentLoaded', function () {
    // Função que será chamada em qualquer campo CEP da aplicação
    function initViaCep() {
        const cepInput = document.getElementById('cep');
        if (!cepInput) return;

        // Preenche os campos automaticamente quando sair do campo CEP
        cepInput.addEventListener('blur', function () {
            let cep = this.value.replace(/\D/g, '');
            if (cep.length !== 8) return;

            fetch(`https://viacep.com.br/ws/${cep}/json/`)
                .then(response => response.json())
                .then(data => {
                    if (data.erro) {
                        alert('CEP não encontrado!');
                        return;
                    }

                    // Preenche todos os campos de endereço em MAIÚSCULAS
                    document.getElementById('logradouro')?.value = (data.logradouro || '').toUpperCase();
                    document.getElementById('bairro')?.value = (data.bairro || '').toUpperCase();
                    document.getElementById('cidade')?.value = (data.localidade || '').toUpperCase();
                    document.getElementById('estado')?.value = (data.uf || '').toUpperCase();

                    // Dá foco no campo número
                    document.getElementById('numero')?.focus();
                })
                .catch(() => {
                    alert('Erro ao buscar o CEP. Verifique sua conexão.');
                });
        });
    }

    // Executa na carga inicial
    initViaCep();

    // Executa também quando um modal é aberto (importantíssimo!)
    document.addEventListener('shown.bs.modal', initViaCep);
}); 