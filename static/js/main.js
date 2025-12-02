// static/js/main.js
document.addEventListener('DOMContentLoaded', function () {

    // =============================================
    // 1. FECHAR MODAIS COM A TECLA ESC
    // =============================================
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            const modaisAbertos = document.querySelectorAll('.modal.show');
            modaisAbertos.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            });
        }
    });

    // =============================================
    // 2. BUSCA DINÂMICA EM TODAS AS TABELAS
    // =============================================
    const searchInputs = document.querySelectorAll('input[data-search]');
    searchInputs.forEach(input => {
        input.addEventListener('input', function () {
            const query = this.value.toUpperCase().trim();
            const tableId = this.dataset.search;
            const table = document.querySelector(tableId);
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toUpperCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    });

    // =============================================
    // 3. TO UPPERCASE AUTOMÁTICO (exceto email)
    // =============================================
    document.querySelectorAll('input.uppercase').forEach(input => {
        if (!input.type.includes('email') && input.id !== 'email') {
            input.addEventListener('input', function () {
                this.value = this.value.toUpperCase();
            });
        }
    });

    // =============================================
    // 4. MOSTRAR/ESCONDER CAMPO GERENTE (só quando for REPRESENTANTE)
    // =============================================
    const tipoUsuarioSelect = document.getElementById('tipo_usuario');
    const gerenteDiv = document.getElementById('div_gerente');

    function toggleGerente() {
        if (!tipoUsuarioSelect || !gerenteDiv) return;

        const tipoSelecionado = tipoUsuarioSelect.options[tipoUsuarioSelect.selectedIndex].text;
        if (tipoSelecionado === 'REPRESENTANTE') {
            gerenteDiv.style.display = 'block';
            gerenteDiv.querySelector('select').setAttribute('required', 'required');
        } else {
            gerenteDiv.style.display = 'none';
            gerenteDiv.querySelector('select').removeAttribute('required');
        }
    }

    if (tipoUsuarioSelect) {
        tipoUsuarioSelect.addEventListener('change', toggleGerente);
        toggleGerente(); // executa na carga da página
    }

    // =============================================
    // 5. POPUP DA FILA DE INTERESSE (Reservas)
    // =============================================
    document.querySelectorAll('[data-fila]').forEach(btn => {
        btn.addEventListener('click', function () {
            const nomes = this.dataset.fila.split(';').filter(n => n.trim());
            const lista = nomes.map(n => `<li class="list-group-item">${n.trim()}</li>`).join('');
            const conteudo = nomes.length > 0
                ? `<ul class="list-group list-group-flush">${lista}</ul>`
                : '<p class="text-muted text-center">Ninguém na fila</p>';

            document.getElementById('filaModalBody').innerHTML = conteudo;
            new bootstrap.Modal(document.getElementById('filaModal')).show();
        });
    });

    // =============================================
    // 6. CONFIRMAÇÃO ANTES DE REJEITAR CONSULTA/RESERVA
    // =============================================
    document.querySelectorAll('button[data-rejeitar]').forEach(btn => {
        btn.addEventListener('click', function () {
            const id = this.dataset.id;
            const tipo = this.dataset.tipo; // consulta ou reserva

            const motivo = prompt('Digite o motivo da rejeição:');
            if (motivo === null) return; // cancelou
            if (motivo.trim() === '') {
                alert('O motivo é obrigatório!');
                return;
            }

            // Envia via fetch
            fetch(`/rejeitar_${tipo}/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ motivo: motivo.trim() })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Erro: ' + data.message);
                }
            });
        });
    });

    // =============================================
    // 7. RENOVAR EM MASSA (botão "Renovar Tudo")
    // =============================================
    document.getElementById('renovar-tudo')?.addEventListener('click', function () {
        if (!confirm('Renovar TODAS as reservas filtradas?')) return;

        const ids = Array.from(document.querySelectorAll('input[name="reserva_ids"]:checked'))
                         .map(cb => cb.value);

        if (ids.length === 0) {
            alert('Nenhuma reserva selecionada.');
            return;
        }

        fetch('/reservas/renovar_massa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: ids })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) location.reload();
            else alert('Erro ao renovar.');
        });
    });

    // =============================================
    // 8. SELECT ALL (checkbox master nas tabelas)
    // =============================================
    document.querySelectorAll('.select-all').forEach(master => {
        master.addEventListener('change', function () {
            const table = this.closest('table');
            table.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = this.checked;
            });
        });
    });

    // =============================================
    // 9. FORMATAR DATAS PARA dd/mm/aaaa NA EXIBIÇÃO
    // =============================================
    document.querySelectorAll('td[data-date], span[data-date]').forEach(el => {
        const iso = el.dataset.date;
        if (iso && iso.includes('-')) {
            const [y, m, d] = iso.split('T')[0].split('-');
            el.textContent = `${d}/${m}/${y}`;
        }
    });

    console.log('main.js carregado com sucesso!');
});