$(document).ready(function () {

    // Calculate the scrollY height
    function calculateScrollY() {
        var windowHeight = $(window).height();
        var footerHeight = $('footer').outerHeight() || 0; // Footer height
        var tableOffsetTop = $('#tasks').offset().top || 0; // Table's top position

        // Calculate the scrollY value        
        var scrollY = windowHeight - footerHeight - (tableOffsetTop - $(window).scrollTop());        
        scrollY = scrollY - 80
        return scrollY + 'px';
    }

    var scrollTop = 0;
    var scrollingContainer;
    var selectedRows = null;

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
            { data: 'modality', title: 'Serie' },
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
        scrollY:        '500px',
        searching:      true,
        info:           true,
        select:         {
                            style: 'os',
                            selector: 'td',
                            info: false,
                        },
        initComplete: function () {
            
            // Keep track of scrolling position for table refresh
            scrollingContainer = $(tasks_table.table().node()).parent('div.dataTables_scrollBody');
            scrollingContainer.on('scroll', function() {
                scrollTop = scrollingContainer.scrollTop();
            });

            // Add click event for row selection
            tasks_table.on( 'select', function () {
                selectedRows = tasks_table.rows({'selected':true})[0]
            });
            refreshTable()
        }
    });

    // Auto refresh, keeping selected rows and scrolling position
    function refreshTable() {
        tasks_table.ajax.reload(function () {
            if (selectedRows !== null) {
                tasks_table.rows(selectedRows).select();
            }
            scrollingContainer.scrollTop(scrollTop);
            setTimeout(refreshTable, 2000);
        });
    }

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