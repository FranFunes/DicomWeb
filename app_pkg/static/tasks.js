$(document).ready(function () {

    var tasks_table = $('#tasks').DataTable({
        ajax: "/get_tasks_table", 
        columns: [
            { data: 'status', title: 'Estado' },
            { data: 'progress', title: 'Progreso' },
            { data: 'started', title: 'Inicio' },
            { data: 'level', title: 'Nivel' },
            { data: 'PatientName', title: 'Paciente' }, 
            { data: 'StudyDate', title: 'Fecha', type: 'date' }, 
            { data: 'description', title: 'Descripcion' },
            { data: 'modality', title: 'Modalidad' },
            { data: 'SeriesNumber', title: 'Numero' },
            { data: 'source', title: 'Origen' },
            { data: 'destination', title: 'Destino' },
            { data: 'imgs', title: 'Imgs' },
            { data: 'type', title: 'Tarea' },
        ],
        order: [[2, 'asc']],
        language: {
            search: 'Buscar',
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: "<br><br>",
            processing: " ",
        }, 
        rowCallback: function(row, data, index) {
          if (data.status == "completed") {
            $("td:eq(0)", row).css('background-color','#8FD548');
          } else if (data.status == "failed") {
            $("td:eq(0)", row).css('background-color','#E23636');
          } else if (data.status == "active") {
            $("td:eq(0)", row).css('background-color','#415058');
          }
          
        },
        processing:     false,
        paging:         false,
        scrollX:        true,  
        searching:      false,
        info:           false,
        select:         {
                            style: 'os',
                            selector: 'td',
                            info: false,
                        },
    });
    
    // Auto refresh, keeping selected rows
    setInterval( function () {
        var selectedRows = tasks_table.rows({ selected: true });
        var idx = selectedRows[0];
               
        tasks_table.ajax.reload( function() {
            idx.forEach(function(element) {
                tasks_table.row(element).select();                
            })
        }); 
    }, 5000);

    // Add buttons functionality
    $('.task-action').on('click', function() {
        selectedRows = tasks_table.rows({ selected: true })
        task_ids = selectedRows.data().toArray().map(item => item.task_id)
        $.ajax({
            url: "/task_action",
            method: "POST",
            data: JSON.stringify({
                'action': $(this).attr('id'),                
                'ids': task_ids,
            }),
            contentType:'application/json'
        })
    })
});

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';