$(document).ready(function () {

    initStudiesTable()
    initDestinations()

});
    

// Initialize studies table
function initStudiesTable() {
    
    var table_studies = $('#studies').DataTable({
        ajax: '/get_local_studies',          
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
            },
            { data: 'PatientName', title: 'Paciente' },
            { data: 'PatientID', title: 'ID' },
            { data: 'StudyDate', title: 'Fecha', type: 'date'},
            { data: 'StudyTime', title: 'Hora' },
            { data: 'ModalitiesInStudy', title: 'Modalidades' },
            { data: 'StudyDescription', title: 'Descripcion' },
            { data: 'ImgsStudy', title: 'Imgs' }
        ],
        order: [[3, 'asc'],[4, 'asc']],
        language: {
            search: 'Buscar',
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: " ",
            processing: " ",
        },
        processing: true,  
        paging: false,
        scrollY: '300px',
        filter: false
    });
    
    // Add event listener for opening and closing details
    $('#studies tbody').on('click', 'td.dt-control', function () {
        var tr = $(this).closest('tr');
        var row = table_studies.row(tr);
 
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
        } else {
            // Open this row
            showStudy(row)            
            tr.addClass('shown');
        }
    });  
    
    // Add row selection behaviour
    $('#studies tbody').on('click', 'tr', function (clickEvent) {  
              
        if (($(this).hasClass('odd') || $(this).hasClass('even')) && !clickEvent.target.classList.contains('dt-control')) {
            $(this).toggleClass('selected toSend');            
        }

    });

    // Add send button behaviour
    $("#sendForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();

        // Get destination device
        var ajax_data = {'destination': $("#destinations").val()}

        // Get selected rows
        var items = []
        var tr = $('.toSend')        
        for (var idx = 0; idx < tr.length; idx++){
            var element = tr[idx]
            items.push($(element.closest('table')).DataTable().row(element).data())                        
        }
        ajax_data.items = items
        $.ajax({
            url: "/move",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {
                
                // Show success message
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });

    });
}

function initDestinations() {
    
    $.ajax({
        url: "/get_devices",
        method: "GET",
        contentType: "application/json",
        success: function(response) {
            
            // Show success message
            console.log(response)
            /*
            var selectValues = $('#devices').DataTable().column(0).data()
            $.each(selectValues, function(key, value) {
                $('#destinations')
                     .append($('<option>', { value : value })
                     .text(value));
                });*/
            
        },
        error: function(xhr, status, error) {
            // handle error response here
            console.log(xhr.responseText);
        }
        });
}

// Show study details
function showStudy(row) {        
    
    row.child(`<table id="child_${row.data().StudyInstanceUID}" class="display compact" width="100%"> 
                
            </table>`).show();
    var childTable = $(jq("child_" + row.data().StudyInstanceUID)).DataTable({
        ajax: {
        url: "/get_study_data",
        method: "POST",
        data: function() { return JSON.stringify(row.data()) },
        contentType: 'application/json',
        dataType: "json"
      },
        columns: [
            
            { data: 'SeriesNumber', title: 'Numero' },
            { data: 'SeriesDate', title: 'Fecha' },
            { data: 'SeriesTime', title: 'Hora' },
            { data: 'SeriesDescription', title: 'Descripcion' },
            { data: 'Modality', title: 'Modalidad' },
            { data: 'ImgsSeries', title:'Imgs' },
            
        ],
        order: [[0, 'asc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: "<br><br>",
            processing: " ",
            loadingRecords: "<br>",
        },
        processing: true,
        paging: false,
        filter: false,
        info: false,
});
}

// Escape special characters in html element id (to be usable by jQuery)
function jq( myid ) {  
    return "#" + myid.replace( /(:|\.|\[|\]|,|=|@)/g, "\\$1" ); 
}

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';